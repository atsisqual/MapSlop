#!/usr/bin/env python3
"""Private conversion of the validated Roofer sample. No Shewchuk Triangle."""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import numpy as np
from pyproj import Transformer
from terrain_binary import decode
from terrain_grid import to_world

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
            with path.open() as fp:cm=cityjson.reader(fp)
            glb=cm.export2glb()
            payload=glb.getvalue()
            if payload[:4]!=b"glTF":raise ValueError("Invalid GLB signature")
            (a.output/(key+".glb")).write_bytes(payload)
            local[key]={"policy":"roofer_lod22_candidate","roof":roof,"walls":wall,
                        "roof_min_y":min(roof[1::3]),"roof_max_y":max(roof[1::3]),
                        "wall_min_y":min(wall[1::3]),"wall_max_y":max(wall[1::3])}
            rows.append({"osm_id":key,"triangles":(len(roof)+len(wall))//9,
                         "glb_bytes":len(payload),"roof_min_y":local[key]["roof_min_y"],"roof_max_y":local[key]["roof_max_y"]})
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
            "triangle_installed":False,"triangulation":"mapbox-earcut via cjio geom_help"}
    (a.output/"roof-conversion-report.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,allow_nan=False),flush=True)
    if len(rows)!=18:raise ValueError("Expected all eighteen reconstructed buildings to convert")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for arg in ("archive","summary","terrain","output"):p.add_argument("--"+arg,type=Path,required=True)
    convert(p.parse_args())
