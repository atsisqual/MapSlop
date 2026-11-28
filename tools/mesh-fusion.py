#!/usr/bin/env python3
"""Offline registration and geometry-only mesh cleanup for authorized assets.

Open3D refines a surveyed initial rigid/similarity pose. Independent controls gate
the result. Textured GLB transforms are written separately without changing UVs.
PyMeshLab cleans explicitly geometry-only PLY; never use it to weld UV seams.
"""
import argparse, importlib.util, json, math
from pathlib import Path
import numpy as np
import open3d as o3d
spec=importlib.util.spec_from_file_location("assets",Path(__file__).with_name("asset-pipeline.py"))
assets=importlib.util.module_from_spec(spec);spec.loader.exec_module(assets)

def matrix4(m):
    m=np.asarray(m,float)
    if m.shape!=(4,4) or not np.isfinite(m).all() or not np.allclose(m[3],[0,0,0,1]):raise ValueError("Invalid affine")
    s=np.linalg.svd(m[:3,:3],compute_uv=False)
    if min(s)<=0 or max(s)/min(s)>1.00001 or np.linalg.det(m[:3,:3])<=0:raise ValueError("Require proper similarity, no reflection or shear")
    return m

def cloud(points,colors=None):
    p=np.asarray(points,float)
    if p.ndim!=2 or p.shape[1]!=3 or len(p)<30 or not np.isfinite(p).all() or np.linalg.matrix_rank(p-p.mean(0))<3:raise ValueError("Require nondegenerate 3D point cloud")
    c=o3d.geometry.PointCloud(o3d.utility.Vector3dVector(p))
    if colors is not None:
        a=np.asarray(colors,float)
        if a.shape!=p.shape or not np.isfinite(a).all() or (a<0).any() or (a>1).any():raise ValueError("Invalid RGB")
        c.colors=o3d.utility.Vector3dVector(a)
    return c

def transform(points,m):
    return np.asarray(points)@m[:3,:3].T+m[:3,3]

def register(source,target,initial,check_source,check_target,voxel=.08,max_error=.05,min_overlap=.55,method="geometry"):
    m=matrix4(initial)
    if not (0<voxel<=10 and 0<max_error<=1 and .1<=min_overlap<=1):raise ValueError("Invalid thresholds")
    x=np.asarray(check_source,float);y=np.asarray(check_target,float)
    if x.shape!=y.shape or x.ndim!=2 or x.shape[1]!=3 or len(x)<3 or not np.isfinite([x,y]).all() or np.linalg.matrix_rank(x-x.mean(0))<2:raise ValueError("Require >=3 independent noncollinear controls")
    # Transform source first so the ICP estimator always sees rigid metric coordinates.
    src=cloud(transform(np.asarray(source.points),m),np.asarray(source.colors) if source.has_colors() else None)
    dst=cloud(np.asarray(target.points),np.asarray(target.colors) if target.has_colors() else None)
    if method not in ("geometry","colored"):raise ValueError("Unknown registration method")
    if method=="colored" and not (src.has_colors() and dst.has_colors()):raise ValueError("Colored ICP requires RGB in both clouds")
    reg=o3d.pipelines.registration;delta=np.eye(4);stages=[]
    for factor in (4,2,1):
        size=voxel*factor;radius=size*2.5
        a=src.voxel_down_sample(size);b=dst.voxel_down_sample(size)
        if min(len(a.points),len(b.points))<30:raise ValueError("Too few points at coarse scale")
        criteria=reg.ICPConvergenceCriteria(max_iteration=60,relative_fitness=1e-7,relative_rmse=1e-7)
        if method=="colored":
            for c in (a,b):c.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=size*3,max_nn=40))
            r=reg.registration_colored_icp(a,b,radius,delta,reg.TransformationEstimationForColoredICP(),criteria)
        else:
            r=reg.registration_icp(a,b,radius,delta,reg.TransformationEstimationPointToPoint(False),criteria)
        delta=matrix4(r.transformation)
        stages.append({"voxel_m":size,"fitness":r.fitness,"rmse_m":r.inlier_rmse,"source_points":len(a.points),"target_points":len(b.points)})
    final=matrix4(delta@m);aligned=cloud(transform(np.asarray(source.points),final))
    # Bidirectional full-resolution overlap; fitness alone can hide an incorrect local minimum.
    fwd=reg.evaluate_registration(aligned,dst,voxel*1.5,np.eye(4))
    rev=reg.evaluate_registration(dst,aligned,voxel*1.5,np.eye(4))
    before=np.linalg.norm(transform(x,m)-y,axis=1);after=np.linalg.norm(transform(x,final)-y,axis=1)
    r={"method":method,"matrix":final.tolist(),"stages":stages,"forward_overlap":fwd.fitness,"reverse_overlap":rev.fitness,"forward_rmse_m":fwd.inlier_rmse,"reverse_rmse_m":rev.inlier_rmse,"independent_before_rmse_m":float(np.sqrt(np.mean(before**2))),"independent_after_rmse_m":float(np.sqrt(np.mean(after**2))),"independent_max_m":float(after.max()),"open3d":o3d.__version__}
    r["pass"]=bool(min(fwd.fitness,rev.fitness)>=min_overlap and max(fwd.inlier_rmse,rev.inlier_rmse)<=voxel and after.max()<=max_error and np.mean(after**2)<=np.mean(before**2)+1e-10)
    return r

def clean_geometry(vertices,faces):
    import pymeshlab as ml
    v=np.asarray(vertices,np.float64);f=np.asarray(faces,np.int32)
    if v.ndim!=2 or v.shape[1]!=3 or f.ndim!=2 or f.shape[1]!=3 or not len(f) or not np.isfinite(v).all() or f.min()<0 or f.max()>=len(v):raise ValueError("Invalid triangle mesh")
    ms=ml.MeshSet();ms.add_mesh(ml.Mesh(vertex_matrix=v,face_matrix=f),"original")
    for name in ("meshing_remove_duplicate_vertices","meshing_remove_null_faces","meshing_remove_duplicate_faces","meshing_remove_unreferenced_vertices"):ms.apply_filter(name)
    m=ms.current_mesh();vv=m.vertex_matrix().copy();ff=m.face_matrix().copy()
    if not len(ff):raise ValueError("Mesh disappeared")
    # No simplification or movement. All surviving triangles must match original nondegenerate triangles in coordinates.
    def signatures(v,f):
        a=v[f];area=np.linalg.norm(np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]),axis=1)
        return {tuple(sorted(tuple(p) for p in tri)) for tri in a[area>1e-12]}
    original=signatures(v,f);actual=signatures(vv,ff)
    r={"input_vertices":len(v),"input_faces":len(f),"output_vertices":len(vv),"output_faces":len(ff),"unique_original_nonzero_triangles":len(original),"geometry_only":True,"pass":actual==original and len(ff)==len(actual)}
    return vv,ff,r

def read_cloud(path):
    if path.suffix.lower()!=".ply":raise ValueError("Use explicit metric PLY point cloud")
    p=o3d.io.read_point_cloud(str(path))
    return cloud(np.asarray(p.points),np.asarray(p.colors) if p.has_colors() else None)

def verified(path,manifest):
    m=assets.provenance(path.parent,manifest)
    if path.name not in m["files"]:raise ValueError("Input not inventoried")
    return m

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("register")
    for name in ("source","target","source-manifest","target-manifest","controls","output"):a.add_argument("--"+name,type=Path,required=True)
    a.add_argument("--voxel",type=float,default=.08);a.add_argument("--max-error",type=float,default=.05);a.add_argument("--min-overlap",type=float,default=.55);a.add_argument("--method",choices=["geometry","colored"],default="geometry");a.add_argument("--glb",type=Path)
    a=sub.add_parser("clean")
    a.add_argument("--mesh",type=Path,required=True);a.add_argument("--manifest",type=Path,required=True);a.add_argument("--output",type=Path,required=True);a.add_argument("--geometry-only",action="store_true",required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    if a.cmd=="register":
        sm=verified(a.source,a.source_manifest);tm=verified(a.target,a.target_manifest);c=json.loads(a.controls.read_text())
        if a.glb:
            if a.glb.parent.resolve()!=a.source.parent.resolve() or a.glb.name not in sm["files"]:raise ValueError("GLB must be inventoried with source cloud in same frame")
            assets.read_glb(a.glb)
        src=read_cloud(a.source);dst=read_cloud(a.target);r=register(src,dst,c["initial_matrix"],c["check_source"],c["check_target"],a.voxel,a.max_error,a.min_overlap,a.method)
        r.update(source_manifest=sm,target_manifest=tm,controls=c,thresholds={"voxel":a.voxel,"max_error":a.max_error,"min_overlap":a.min_overlap})
        if r["pass"]:
            src.transform(np.array(r["matrix"]));out=a.output/"aligned.ply"
            if not o3d.io.write_point_cloud(str(out),src):raise RuntimeError("Write failed")
            r["aligned_sha256"]=assets.sha(out)
            if a.glb:
                out=a.output/"aligned.glb";assets.align_glb(a.glb,out,r["matrix"]);r["glb_sha256"]=assets.sha(out)
    else:
        m=verified(a.mesh,a.manifest)
        if a.mesh.suffix.lower()!=".ply":raise ValueError("Geometry-only PLY required")
        # Require declared geometry-only source; never discard textures or vertex colors silently.
        if m.get("geometry_only") is not True:raise ValueError("Manifest must declare geometry_only")
        mesh=o3d.io.read_triangle_mesh(str(a.mesh))
        if mesh.has_vertex_colors() or mesh.has_triangle_uvs() or mesh.has_textures():raise ValueError("Attribute-bearing mesh rejected")
        v,f,r=clean_geometry(np.asarray(mesh.vertices),np.asarray(mesh.triangles));r["source_manifest"]=m
        if r["pass"]:
            out=a.output/"clean.ply";mm=o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(v),o3d.utility.Vector3iVector(f));mm.compute_vertex_normals()
            if not o3d.io.write_triangle_mesh(str(out),mm):raise RuntimeError("Write failed")
            r["output_sha256"]=assets.sha(out)
    (a.output/"report.json").write_text(json.dumps(r,indent=2,allow_nan=False)+"\n");print("MESH_FUSION",json.dumps(r))
    if not r["pass"]:raise SystemExit("Validation failed; no candidate exported")
if __name__=="__main__":main()
