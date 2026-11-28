#!/usr/bin/env python3
"""Convert candidate SUMO lanes or 3dfier semantic OBJ to MapSlop's local metric frame.
Never modify the road graph, TIN or game. Source projection and vertical datum are explicit.
"""
import argparse, hashlib, json, math, struct, xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from pyproj import CRS, Transformer
from terrain_grid import ORIGIN, to_world

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def projector(crs,origin=ORIGIN):
    from terrain_grid import KX,KY
    if not CRS.from_user_input(crs).is_projected:raise ValueError("Projected source CRS required")
    tr=Transformer.from_crs(crs,4326,always_xy=True)
    def f(x,y):
        lon,lat=tr.transform(x,y,errcheck=True)
        if not np.isfinite([lon,lat]).all():raise ValueError("Invalid projected coordinate")
        return (np.asarray(lon)-origin[1])*KX,-(np.asarray(lat)-origin[0])*KY
    return f

def sumo(net,osm):
    root=ET.parse(net).getroot();loc=root.find("location")
    if loc is None:raise ValueError("Missing SUMO projection")
    dx,dy=map(float,loc.attrib["netOffset"].split(","))
    project=projector(loc.attrib["projParameter"])
    def point(x,y):
        a,b=project(x-dx,y-dy);return [float(a),float(b)]
    # Independent coordinate comparisons against original exact OSM node IDs.
    source={n.get("id"):(float(n.get("lon")),float(n.get("lat"))) for n in ET.parse(osm).getroot().findall("node")}
    controls=[]
    for j in root.findall("junction"):
        i=j.get("id")
        if i not in source or j.get("type")=="internal":continue
        actual=point(float(j.get("x")),float(j.get("y")))
        expected=to_world(*source[i]);err=math.hypot(actual[0]-expected[0],actual[1]-expected[1])
        controls.append({"osm_node":i,"error_m":err})
    if len(controls)<3:raise ValueError("Insufficient identifiable OSM junction controls")
    errors=np.array([c["error_m"] for c in controls])
    # Junction centers can legitimately move when SUMO joins/splits nodes. Report,
    # never discard moved controls or imply surveyed alignment.
    lanes=[]
    for e in root.findall("edge"):
        if e.get("function"):continue
        for l in e.findall("lane"):
            coords=[]
            for item in l.attrib["shape"].split():
                xyz=list(map(float,item.split(",")))
                coords.append(point(*xyz[:2]))
            if len(coords)<2:raise ValueError("Lane without geometry")
            lanes.append({"edge":e.get("id"),"lane":l.get("id"),"from":e.get("from"),"to":e.get("to"),"index":int(l.get("index")),"width_m":float(l.get("width",3.2)),"width_estimated":l.get("width") is None,"xz":coords})
    if not lanes:raise ValueError("Empty network")
    report={"pass":bool(np.percentile(errors,95)<=.5 and errors.max()<=2),"lanes":len(lanes),"controls":controls,"control_rmse_m":float(np.sqrt(np.mean(errors**2))),"control_p95_m":float(np.percentile(errors,95)),"control_max_m":float(errors.max()),"projection":loc.attrib,"frame":"MapSlop X east/Z south; no elevation; SUMO lanes inferred"}
    return lanes,report

def obj_to_glb(source,dest,crs,vertical_base):
    # 3dfier OBJ is XYZ projected metres, semantic materials. Reject texture or
    # normal indices: this adapter is for untextured semantic lifted geometry.
    verts=[];groups={};material="unknown"
    for line in source.read_text().splitlines():
        l=line.split()
        if not l:continue
        if l[0]=="v":
            if len(l)!=4:raise ValueError("Unexpected vertex attributes")
            verts.append(list(map(float,l[1:])))
        elif l[0]=="usemtl":material=" ".join(l[1:])
        elif l[0] in ("vt","vn"):raise ValueError("Use textured Blender converter instead")
        elif l[0]=="f":
            if len(l)!=4 or any("/" in i for i in l[1:]):raise ValueError("Require plain triangulated OBJ")
            ids=[int(i)-1 for i in l[1:]]
            if min(ids)<0 or max(ids)>=len(verts):raise ValueError("Bad OBJ index")
            groups.setdefault(material,[]).append(ids)
    v=np.asarray(verts,float)
    if not len(v) or not groups or not np.isfinite(v).all() or not math.isfinite(vertical_base):raise ValueError("Invalid mesh")
    project=projector(crs)
    x,z=project(v[:,0],v[:,1]);p=np.column_stack((x,v[:,2]-vertical_base,z))
    if np.max(np.abs(p))>1_000_000:raise ValueError("Nonlocal geometry")
    blob=bytearray();views=[];accessors=[];prims=[];materials=[];stats={}
    def attribute(a):
        a=np.asarray(a,dtype="<f4");i=len(views);views.append({"buffer":0,"byteOffset":len(blob),"byteLength":a.nbytes,"target":34962});blob.extend(a.tobytes())
        j=len(accessors);accessors.append({"bufferView":i,"componentType":5126,"count":len(a),"type":"VEC3","min":a.min(0).tolist(),"max":a.max(0).tolist()});return j
    for name,faces in groups.items():
        t=p[np.asarray(faces)];n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);length=np.linalg.norm(n,axis=1)
        if (length<=1e-9).any():raise ValueError("Degenerate transformed triangle")
        pos=t.reshape(-1,3);normals=np.repeat(n/length[:,None],3,axis=0)
        color=[.48,.48,.48,1] if name.lower()=="road" else [.6,.57,.51,1]
        k=len(materials);materials.append({"name":name,"doubleSided":True,"pbrMetallicRoughness":{"baseColorFactor":color,"metallicFactor":0,"roughnessFactor":1}})
        prims.append({"attributes":{"POSITION":attribute(pos),"NORMAL":attribute(normals)},"material":k,"mode":4})
        stats[name]={"triangles":len(faces),"height_range_m":[float(pos[:,1].min()),float(pos[:,1].max())]}
    j={"asset":{"version":"2.0","generator":"MapSlop lifted infrastructure"},"scene":0,"scenes":[{"nodes":[0]}],"nodes":[{"mesh":0}],"meshes":[{"primitives":prims}],"materials":materials,"buffers":[{"byteLength":len(blob)}],"bufferViews":views,"accessors":accessors}
    h=json.dumps(j,separators=(",",":"),allow_nan=False).encode();h+=b" "*((-len(h))%4)
    dest.write_bytes(struct.pack("<4sII",b"glTF",2,28+len(h)+len(blob))+struct.pack("<I4s",len(h),b"JSON")+h+struct.pack("<I4s",len(blob),b"BIN\0")+blob)
    return {"pass":True,"source_crs":str(crs),"vertical_base_m":vertical_base,"source_vertices":len(v),"triangles":sum(len(f) for f in groups.values()),"semantic_materials":stats,"bounds":[p.min(0).tolist(),p.max(0).tolist()],"glb_sha256":sha(dest),"frame":"MapSlop X east/Y up/Z south. Vertical datum supplied by caller; not transformed.","material_policy":"neutral semantic colors, not real texture"}
def main():
    ap=argparse.ArgumentParser();s=ap.add_subparsers(dest="mode",required=True)
    a=s.add_parser("sumo");a.add_argument("net",type=Path);a.add_argument("osm",type=Path);a.add_argument("output",type=Path)
    a=s.add_parser("3dfier");a.add_argument("obj",type=Path);a.add_argument("output",type=Path);a.add_argument("--source-crs",required=True);a.add_argument("--vertical-base",type=float,required=True)
    a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    if a.mode=="sumo":
        lanes,r=sumo(a.net,a.osm);r.update(input_sha256=sha(a.net),osm_sha256=sha(a.osm))
        if r["pass"]:(a.output/"lanes.json").write_text(json.dumps(lanes,separators=(",",":"),allow_nan=False))
    else:r=obj_to_glb(a.obj,a.output/"candidate.glb",a.source_crs,a.vertical_base);r["input_sha256"]=sha(a.obj)
    (a.output/"report.json").write_text(json.dumps(r,indent=2,allow_nan=False)+"\n");print("INFRA_FRAME",json.dumps({k:v for k,v in r.items() if k!="controls"}))
    if not r["pass"]:raise SystemExit("Coordinate QA failed; no lane candidate written")
if __name__=="__main__":main()
