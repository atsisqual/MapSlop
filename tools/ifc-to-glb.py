#!/usr/bin/env python3
"""IFC BIM -> self-contained GLB. Metric, Y-up local coordinates; retain element GUIDs.
Uses IfcOpenShell geometry, not render-time IFC parsing. Geometry and materials only.
"""
import argparse,hashlib,json,struct
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.geom
def convert(source,output,origin):
    model=ifcopenshell.open(str(source));settings=ifcopenshell.geom.settings();settings.set("use-world-coords",True)
    origin=np.asarray(origin,dtype=float)
    if origin.shape!=(3,) or not np.isfinite(origin).all():raise ValueError("Invalid IFC origin")
    payload=bytearray();views=[];accessors=[];meshes=[];nodes=[];rows=[]
    def attrib(a,kind):
        a=np.asarray(a,dtype="<f4");i=len(views);views.append({"buffer":0,"byteOffset":len(payload),"byteLength":a.nbytes,"target":34962});payload.extend(a.tobytes())
        j=len(accessors);accessors.append({"bufferView":i,"componentType":5126,"count":len(a),"type":kind,"min":a.min(0).tolist(),"max":a.max(0).tolist()});return j
    for e in model.by_type("IfcElement"):
        if e.is_a("IfcOpeningElement") or not getattr(e,"Representation",None):continue
        shape=ifcopenshell.geom.create_shape(settings,e)
        v=np.asarray(shape.geometry.verts,dtype=float).reshape(-1,3)-origin
        f=np.asarray(shape.geometry.faces,dtype=int).reshape(-1,3)
        if not len(f) or not np.isfinite(v).all() or f.min()<0 or f.max()>=len(v):raise ValueError("Invalid IFC mesh "+e.GlobalId)
        # IFC X,Y horizontal Z up -> glTF X east, Y up, Z south (proper rotation).
        v=np.column_stack((v[:,0],v[:,2],-v[:,1]));tris=v[f]
        n=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]);l=np.linalg.norm(n,axis=1);valid=l>1e-10
        tris=tris[valid];n=n[valid]/l[valid,None]
        if not len(tris):raise ValueError("Empty IFC mesh")
        p=tris.reshape(-1,3);normals=np.repeat(n,3,axis=0)
        if np.max(np.abs(p))>10000:raise ValueError("Use explicit local origin; precision guard")
        name=e.GlobalId;idx=len(meshes);meshes.append({"name":name,"primitives":[{"attributes":{"POSITION":attrib(p,"VEC3"),"NORMAL":attrib(normals,"VEC3")},"material":0,"mode":4}]});nodes.append({"name":name,"mesh":idx,"extras":{"ifc_class":e.is_a(),"ifc_guid":name}})
        rows.append({"guid":name,"ifc_class":e.is_a(),"triangles":len(tris),"bounds":[p.min(0).tolist(),p.max(0).tolist()]})
    if not rows:raise ValueError("No represented IfcElements")
    doc={"asset":{"version":"2.0","generator":"MapSlop IfcOpenShell candidate"},"scene":0,"scenes":[{"nodes":list(range(len(nodes)))}],"nodes":nodes,"meshes":meshes,"materials":[{"name":"Neutral estimated material","pbrMetallicRoughness":{"baseColorFactor":[.7,.7,.7,1],"metallicFactor":0,"roughnessFactor":.85}}],"bufferViews":views,"accessors":accessors,"buffers":[{"byteLength":len(payload)}]}
    header=json.dumps(doc,separators=(",",":"),allow_nan=False).encode();header+=b" "*((-len(header))%4)
    output.write_bytes(struct.pack("<4sII",b"glTF",2,28+len(header)+len(payload))+struct.pack("<I4s",len(header),b"JSON")+header+struct.pack("<I4s",len(payload),b"BIN\0")+payload)
    return {"pass":True,"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"output_sha256":hashlib.sha256(output.read_bytes()).hexdigest(),"ifcopenshell":ifcopenshell.version,"schema":model.schema,"origin_ifc_xyz_m":origin.tolist(),"elements":rows,"material_policy":"neutral; source BIM material/UV not preserved","georef":"local orientation only; independent geographic controls required"}
def main():
    p=argparse.ArgumentParser();p.add_argument("input",type=Path);p.add_argument("output",type=Path);p.add_argument("--origin",nargs=3,type=float,required=True);p.add_argument("--input-sha256",required=True);a=p.parse_args()
    if hashlib.sha256(a.input.read_bytes()).hexdigest()!=a.input_sha256:raise ValueError("Source hash mismatch")
    a.output.mkdir(parents=True,exist_ok=False);r=convert(a.input,a.output/"scene.glb",a.origin);(a.output/"report.json").write_text(json.dumps(r,indent=2)+"\n");print("IFC_CONVERSION",json.dumps(r))
if __name__=="__main__":main()
