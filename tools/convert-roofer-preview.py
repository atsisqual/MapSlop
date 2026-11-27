#!/usr/bin/env python3
"""Private conversion of the validated Roofer sample. No Shewchuk Triangle."""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile
import struct
from copy import deepcopy
import tempfile
import numpy as np
from pyproj import Transformer
from terrain_binary import decode
from terrain_grid import to_world, ORIGIN
from terrain_tin import TinSampler

def read_features(archive):
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            if not member.isfile() or not member.name.endswith(".jsonl"):continue
            header=None
            for line in tar.extractfile(member):
                obj=json.loads(line)
                if obj.get("type")=="CityJSON":
                    header=obj
                    continue
                if obj.get("type")=="CityJSONFeature":
                    if header is None:raise ValueError("CityJSONSeq missing transform header")
                    yield header,obj

def surfaces(geometry):
    vals=geometry.get("semantics",{}).get("values")
    kinds=geometry.get("semantics",{}).get("surfaces",[])
    def kind(i):return kinds[i]["type"] if isinstance(i,int) and 0<=i<len(kinds) else None
    if geometry["type"]=="Solid":
        for shell,sv in zip(geometry["boundaries"],vals or []):
            for face,index in zip(shell,sv):yield face,kind(index)
    elif geometry["type"] in ("MultiSurface","CompositeSurface"):
        for face,index in zip(geometry["boundaries"],vals or []):yield face,kind(index)

def glb_world_bounds(payload):
    if payload[:4]!=b"glTF" or struct.unpack_from("<II",payload,4)!=(2,len(payload)):
        raise ValueError("Invalid GLB header")
    length,kind=struct.unpack_from("<II",payload,12)
    if kind!=0x4e4f534a:raise ValueError("Missing GLB JSON chunk")
    doc=json.loads(payload[20:20+length])
    chunk=20+length
    n,k=struct.unpack_from("<II",payload,chunk)
    if k!=0x004e4942:raise ValueError("Missing GLB BIN chunk")
    raw=payload[chunk+8:chunk+8+n]
    pts=[]
    def walk(i,mat):
        node=doc["nodes"][i]
        if any(x in node for x in ("translation","rotation","scale")):raise ValueError("Unexpected GLB TRS")
        M=mat@np.asarray(node.get("matrix",np.eye(4).ravel()),dtype=float).reshape(4,4).T
        if "mesh" in node:
            for p in doc["meshes"][node["mesh"]]["primitives"]:
                a=doc["accessors"][p["attributes"]["POSITION"]];v=doc["bufferViews"][a["bufferView"]]
                if a["componentType"]!=5126 or a["type"]!="VEC3" or v.get("byteStride",12)!=12:raise ValueError("Unexpected GLB accessor")
                pos=np.frombuffer(raw,dtype="<f4",count=3*a["count"],offset=v.get("byteOffset",0)+a.get("byteOffset",0)).reshape(-1,3)
                pts.extend(pos@M[:3,:3].T+M[:3,3])
        for child in node.get("children",[]):walk(child,M)
    for i in doc["scenes"][doc.get("scene",0)]["nodes"]:walk(i,np.eye(4))
    a=np.asarray(pts)
    if not len(a) or not np.isfinite(a).all():raise ValueError("Invalid GLB positions")
    return a.min(axis=0),a.max(axis=0)

def convert(a):
    from cjio import cityjson,geom_help
    # cjio GLB exporter calls its triangulation helper without sloppy argument.
    # Explicitly use MIT mapbox-earcut; never import/install Triangle.
    original_triangulate=geom_help.triangulate_face
    def earcut(face,vertices,sloppy=True):
        return original_triangulate(face,vertices,sloppy=True)
    geom_help.triangulate_face=earcut
    if getattr(geom_help,"MODULE_TRIANGLE_AVAILABLE",False):
        raise ValueError("Triangle must not be installed in conversion environment")
    summary=json.loads(a.summary.read_text())
    expected={str(row["osm_id"]):row for row in summary["rows"]}
    if summary["requested"]!=20 or summary["with_lod22_geometry"]!=18 or summary["exit_code"]!=0:
        raise ValueError("Expected reviewed 18/20 Roofer result")
    terrain=decode(a.terrain.read_bytes())
    sampler=TinSampler(terrain)
    print('VERTICAL_REFERENCE',json.dumps({'origin_lat_lon':list(ORIGIN),'base_absolute_m':terrain['base'],'terrain_at_origin_m':sampler(0,0),'source_crs':'EPSG:3763 horizontal; source vertical elevations preserved','runtime_y':'absolute source altitude minus terrain base'}),flush=True)
    transform=Transformer.from_crs(3763,4326,always_xy=True)
    a.output.mkdir(parents=True,exist_ok=False)
    local={};rows=[]
    for header,feature in read_features(a.archive):
        key=str(feature.get("id"))
        if key not in expected or key in local:continue
        source=expected[key]
        if source["lod22_geometries"]==0:
            local[key]={"policy":"procedural_fallback","reason":source.get("fallback_reason","no_lod22")}
            continue
        try:
            tr=header.get("transform")
            if not tr:raise ValueError("Missing CityJSON transform")
            crs=header.get("metadata",{}).get("referenceSystem","")
            if crs and not crs.endswith("/3763"):raise ValueError("Unexpected CityJSON CRS: "+crs)
            vv=np.asarray(feature["vertices"],dtype=float)*np.asarray(tr["scale"])+np.asarray(tr["translate"])
            if not np.isfinite(vv).all() or len(vv)<3:raise ValueError("Invalid vertices")
            lon,lat=transform.transform(vv[:,0],vv[:,1])
            world=np.array([[*to_world(x,z),h-terrain["base"]] for x,z,h in zip(lon,lat,vv[:,2])])
            world=world[:,[0,2,1]]
            if np.any(np.abs(world[:,0])>2000) or np.any(np.abs(world[:,2])>2000) or np.any(np.abs(world[:,1])>500):
                raise ValueError("Coordinate frame check failed")
            model={"type":"CityJSON","version":header["version"],"transform":tr,
                   "metadata":{"referenceSystem":"https://www.opengis.net/def/crs/EPSG/0/3763"},
                   "CityObjects":{},"vertices":feature["vertices"]}
            roof=[];wall=[]
            for oid,o in feature["CityObjects"].items():
                geoms=[g for g in o.get("geometry",[]) if str(g.get("lod"))=="2.2"]
                if not geoms:continue
                model["CityObjects"][oid]={"type":o["type"],"geometry":geoms}
                for g in geoms:
                    for face,kind in surfaces(g):
                        if kind not in ("RoofSurface","WallSurface"):continue
                        tris,ok=earcut(face,vv)
                        if not ok:raise ValueError("Earcut failed for semantic surface")
                        for tri in tris:
                            q=world[np.asarray(tri,dtype=int)]
                            if np.linalg.norm(np.cross(q[1]-q[0],q[2]-q[0]))<1e-6:continue
                            (roof if kind=="RoofSurface" else wall).extend(np.round(q,3).ravel().tolist())
            if not roof or not wall:raise ValueError("Missing semantic roof/walls")
            path=a.output/(key+".city.json")
            path.write_text(json.dumps(model,separators=(",",":")))
            # cjio's root maps (east,north,up) -> (x,y,z)=(east,up,-north).
            # Keep original CityJSON for interoperability, but export a separate local model.
            local_model=deepcopy(model)
            local_model['metadata']={'identifier':'MapSlop local metres; origin '+str(ORIGIN)}
            local_model['vertices']=np.rint(world[:,[0,2,1]]*np.array([1,-1,1])*1000).astype(int).tolist()
            local_model['transform']={'scale':[.001,.001,.001],'translate':[0,0,0]}
            cm=cityjson.CityJSON(j=local_model)
            glb=cm.export2glb()
            payload=glb.getvalue()
            glb_min,glb_max=glb_world_bounds(payload)
            used=[]
            for o in model["CityObjects"].values():
                def flatten_indices(x):
                    if isinstance(x,int):used.append(x)
                    elif isinstance(x,list):
                        for v in x:flatten_indices(v)
                for g in o["geometry"]:flatten_indices(g["boundaries"])
            expected_world=world[np.asarray(used,dtype=int)]
            frame_error=max(float(np.max(np.abs(glb_min-expected_world.min(axis=0)))),float(np.max(np.abs(glb_max-expected_world.max(axis=0)))))
            if frame_error>.002:raise ValueError(f"GLB/world bbox mismatch {frame_error}")
            roof_xyz=np.asarray(roof).reshape(-1,3)
            ground=np.asarray([sampler(x,z) for x,_,z in roof_xyz])
            clearance=roof_xyz[:,1]-ground
            (a.output/(key+".glb")).write_bytes(payload)
            local[key]={"policy":"roofer_lod22_candidate","roof":roof,"walls":wall,
                        "roof_min_y":min(roof[1::3]),"roof_max_y":max(roof[1::3]),
                        "wall_min_y":min(wall[1::3]),"wall_max_y":max(wall[1::3])}
            rows.append({"osm_id":key,"triangles":(len(roof)+len(wall))//9,
                         "glb_bytes":len(payload),"roof_min_y":local[key]["roof_min_y"],"roof_max_y":local[key]["roof_max_y"],
                         "absolute_roof_min_m":local[key]["roof_min_y"]+terrain["base"],"absolute_roof_max_m":local[key]["roof_max_y"]+terrain["base"],
                         "terrain_under_roof_min_y":float(ground.min()),"terrain_under_roof_max_y":float(ground.max()),"roof_clearance_min_m":float(clearance.min()),
                         "glb_world_min":glb_min.tolist(),"glb_world_max":glb_max.tolist(),"glb_frame_error_m":frame_error})
        except Exception as e:
            local[key]={"policy":"procedural_fallback","reason":f"conversion_failed: {type(e).__name__}: {e}"}
    for key in expected:
        local.setdefault(key,{"policy":"procedural_fallback","reason":"missing_feature"})
    payload=json.dumps(local,separators=(",",":"),allow_nan=False).encode()
    (a.output/"roof-preview.json").write_bytes(payload)
    report={"requested":20,"converted":len(rows),"fallback":20-len(rows),"rows":rows,
            "policies":{k:{x:v for x,v in row.items() if x not in ("roof","walls")} for k,row in local.items()},
            "runtime_json_bytes":len(payload),"runtime_json_gzip_bytes":len(gzip.compress(payload,mtime=0)),
            "terrain_sha256":hashlib.sha256(a.terrain.read_bytes()).hexdigest(),
            "vertical_reference":{"base_absolute_m":terrain["base"],"origin_lat_lon":list(ORIGIN),"terrain_at_origin_m":sampler(0,0),"glb_frame":"MapSlop x east,y up,z south metres"},
            "glb_frame_verified":len(rows)==18 and all(row["glb_frame_error_m"]<=.002 for row in rows),
            "triangle_installed":False,"triangulation":"mapbox-earcut via cjio geom_help"}
    (a.output/"roof-conversion-report.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,allow_nan=False),flush=True)
    if len(rows)!=18:raise ValueError("Expected all eighteen reconstructed buildings to convert")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for arg in ("archive","summary","terrain","output"):p.add_argument("--"+arg,type=Path,required=True)
    convert(p.parse_args())
