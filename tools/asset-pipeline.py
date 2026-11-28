#!/usr/bin/env python3
"""Local, offline ingestion of already-authorized assets; no vendor map access.
Coordinate control points are in source glTF Y-up and MapSlop X east/Y up/Z south metres.
"""
import argparse, hashlib, json, math, struct
from pathlib import Path
import numpy as np

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def provenance(root,manifest):
    m=json.loads(manifest.read_text())
    for k in ("source_type","license","author","reviewed_by","source_url_or_archive","files"):
        if not m.get(k):raise ValueError("Missing provenance: "+k)
    if m["source_type"] not in ("synthetic","DGT_LiDAR","DGT_orthophoto","owner_authorized_photos","authorized_open_asset"):
        raise ValueError("Source not authorized")
    if any(x in json.dumps(m).lower() for x in ("google earth","google maps","street view","portoslop","maps.google","earth.google")):raise ValueError("Excluded source")
    for name,digest in m["files"].items():
        p=(root/name).resolve()
        if not p.is_relative_to(root.resolve()) or not p.is_file() or sha(p)!=digest:raise ValueError("File verification failed: "+name)
    return m

def similarity(source,target,check_source,check_target,max_error=.5):
    a,b,c,d=map(lambda x:np.asarray(x,dtype=np.float64),(source,target,check_source,check_target))
    if a.shape!=b.shape or a.ndim!=2 or a.shape[1]!=3 or len(a)<3 or c.shape!=d.shape or c.ndim!=2 or c.shape[1]!=3 or len(c)<1 or not all(np.isfinite(x).all() for x in (a,b,c,d)):raise ValueError("Invalid controls")
    x=a-a.mean(0);y=b-b.mean(0)
    if np.linalg.matrix_rank(x)<2:raise ValueError("Collinear fit controls")
    u,s,v=np.linalg.svd(x.T@y);fix=np.eye(3);fix[-1,-1]=np.linalg.det(u@v)
    R=(u@fix@v).T
    scale=float(np.sum(s*np.diag(fix))/np.sum(x*x))
    t=b.mean(0)-scale*R@a.mean(0)
    if not 0<scale<1e6:raise ValueError("Invalid scale")
    residual=lambda p,q:np.linalg.norm((scale*(p@R.T)+t)-q,axis=1)
    fit_err=residual(a,b);check_err=residual(c,d)
    matrix=np.eye(4);matrix[:3,:3]=scale*R;matrix[:3,3]=t
    return {"matrix":matrix.tolist(),"scale":scale,"fit_rmse_m":float(np.sqrt(np.mean(fit_err**2))),"check_max_m":float(check_err.max()),"check_rmse_m":float(np.sqrt(np.mean(check_err**2))),"pass":bool(fit_err.max()<=max_error and check_err.max()<=max_error)}

def read_glb(path):
    data=path.read_bytes()
    magic,version,total=struct.unpack_from("<4sII",data)
    if magic!=b"glTF" or version!=2 or total!=len(data):raise ValueError("Invalid GLB")
    n,kind=struct.unpack_from("<I4s",data,12)
    if kind!=b"JSON":raise ValueError("Missing GLB JSON")
    j=json.loads(data[20:20+n]);rest=data[20+n:]
    if any("uri" in x for x in j.get("buffers",[])+j.get("images",[])):raise ValueError("Require self-contained GLB")
    if not j.get("meshes") or not j.get("scenes"):raise ValueError("Empty mesh")
    return j,rest

def write_glb(path,j,rest):
    h=json.dumps(j,separators=(",",":"),allow_nan=False).encode();h+=b" "*((-len(h))%4)
    path.write_bytes(struct.pack("<4sII",b"glTF",2,20+len(h)+len(rest))+struct.pack("<I4s",len(h),b"JSON")+h+rest)

def align_glb(src,dest,matrix):
    j,rest=read_glb(src);nodes=j.setdefault("nodes",[])
    # Insert a parent in each scene rather than transforming source vertices and corrupting normals.
    for scene in j["scenes"]:
        children=scene.get("nodes",[])
        scene["nodes"]=[len(nodes)]
        nodes.append({"name":"MapSlop surveyed alignment","matrix":np.asarray(matrix).T.flatten().tolist(),"children":children})
    write_glb(dest,j,rest)

def tile_set(entries):
    # Explicit local bounds Y-up in metres; glTF default axis rotation in 3D Tiles.
    def box(lo,hi):
        l=np.array(lo);h=np.array(hi)
        if l.shape!=(3,) or h.shape!=(3,) or not np.isfinite([l,h]).all() or (h<l).any():raise ValueError("Invalid bounds")
        x,y,z=(l+h)/2;a,b,c=(h-l)/2
        return [float(v) for v in (x,-z,y,a,0,0,0,c,0,0,0,b)]
    if not entries:raise ValueError("Empty tiles")
    nodes=[];seen=set()
    for e in entries:
        uri=e["uri"]
        if Path(uri).name!=uri or not uri.endswith(".glb") or uri in seen:raise ValueError("Invalid tile uri")
        seen.add(uri)
        nodes.append({"boundingVolume":{"box":box(*e["bounds"])},"geometricError":0,"refine":"REPLACE","content":{"uri":uri}})
    lo=np.min([e["bounds"][0] for e in entries],axis=0);hi=np.max([e["bounds"][1] for e in entries],axis=0)
    # Root has no content; leaves hold independent spatial blocks.
    return {"asset":{"version":"1.1"},"geometricError":max(1.,float(np.linalg.norm(hi-lo))),"root":{"boundingVolume":{"box":box(lo,hi)},"geometricError":max(1.,float(np.linalg.norm(hi-lo))),"refine":"ADD","children":nodes}}

def main():
    p=argparse.ArgumentParser();p.add_argument("input",type=Path);p.add_argument("manifest",type=Path);p.add_argument("controls",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args();m=provenance(a.input.parent,a.manifest);c=json.loads(a.controls.read_text())
    if a.input.name not in m["files"]:raise ValueError("Input not inventoried")
    r=similarity(c["source"],c["target"],c["check_source"],c["check_target"])
    if not r["pass"]:raise ValueError("Independent alignment check failed")
    a.output.mkdir(parents=True,exist_ok=False);out=a.output/"aligned.glb"
    align_glb(a.input,out,r["matrix"]);r.update(input_sha256=sha(a.input),output_sha256=sha(out),source=m,controls=c)
    (a.output/"alignment.json").write_text(json.dumps(r,indent=2,allow_nan=False)+"\n");print(json.dumps(r))
if __name__=="__main__":main()
