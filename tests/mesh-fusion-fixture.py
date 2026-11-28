"""Real Open3D/PyMeshLab executable-library fixtures, no mocks or downloads."""
import importlib.util,json,sys,math
from pathlib import Path
import numpy as np
import open3d as o3d
spec=importlib.util.spec_from_file_location("fusion",Path(__file__).resolve().parents[1]/"tools/mesh-fusion.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
rng=np.random.default_rng(731)
# Three orthogonal textured surfaces, non-symmetric geometry, partial overlap.
p=np.concatenate([np.c_[rng.uniform(-2,2,2400),rng.uniform(-1,1,2400),np.zeros(2400)],np.c_[rng.uniform(-2,2,1600),np.zeros(1600),rng.uniform(0,2,1600)],np.c_[np.full(1200,-1.5),rng.uniform(-1,1,1200),rng.uniform(0,2,1200)]])
colors=np.clip(.5+.35*np.sin(p*np.array([4,6,7])+np.array([0,1,2])),0,1)
angle=.18;c,s=math.cos(angle),math.sin(angle)
truth=np.array([[c,0,s,.31],[0,1,0,-.12],[-s,0,c,.24],[0,0,0,1.]])
initial=truth.copy();initial[:3,3]+=[.065,-.04,.07]
check=np.array([[.4,.3,1.2],[-1,.2,.5],[.7,-.6,.8],[1,.9,.2]])
source=m.cloud(p[p[:,0]<1.65],colors[p[:,0]<1.65])
target=m.cloud(m.transform(p[p[:,0]>-1.8],truth),colors[p[:,0]>-1.8])
r=m.register(source,target,initial,check,m.transform(check,truth),.065,.045,.65)
assert r["pass"],r
assert r["independent_after_rmse_m"]<.035 and r["independent_after_rmse_m"]<r["independent_before_rmse_m"]*.5,r
bad=m.register(source,target,initial,check,m.transform(check,truth)+[.5,0,0],.065,.045,.65)
assert not bad["pass"],bad
# Colored ICP is an alternative, not a guarantee for repetitive imagery.
colored=m.register(source,target,initial,check,m.transform(check,truth),.065,.05,.65,"colored")
assert colored["pass"],colored
# Merge two overlapping, explicitly untextured triangular pieces with exact duplicate coordinates.
v=np.array([[0,0,0],[1,0,0],[0,1,0],[1,1,0],[1,0,0],[0,1,0],[2,2,2]],float)
f=np.array([[0,1,2],[4,3,5],[0,4,5],[1,4,2]],int)
vv,ff,clean=m.clean_geometry(v,f)
assert clean["pass"] and len(vv)==4 and len(ff)==2,clean
# Test actual GLB parent transform preserves BIN chunk (UV/image data).
import struct
j={"asset":{"version":"2.0"},"scenes":[{"nodes":[0]}],"nodes":[{"mesh":0}],"meshes":[{"primitives":[{"attributes":{"POSITION":0}}]}],"buffers":[{"byteLength":36}],"bufferViews":[{"buffer":0,"byteLength":36}],"accessors":[{"bufferView":0,"componentType":5126,"count":3,"type":"VEC3","min":[0,0,0],"max":[1,1,0]}]}
b=struct.pack("<9f",0,0,0,1,0,0,0,1,0);rest=struct.pack("<I4s",len(b),b"BIN\0")+b
m.assets.write_glb(out/"fixture.glb",j,rest);m.assets.align_glb(out/"fixture.glb",out/"aligned.glb",r["matrix"]);j2,b2=m.assets.read_glb(out/"aligned.glb")
assert b2==rest and np.allclose(np.array(j2["nodes"][-1]["matrix"]).reshape(4,4).T,r["matrix"])
for name,pc in [("source",source),("target",target)]:assert o3d.io.write_point_cloud(str(out/(name+".ply")),pc)
assert o3d.io.write_triangle_mesh(str(out/"clean.ply"),o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(vv),o3d.utility.Vector3iVector(ff)))
from importlib.metadata import version
report={"pass":True,"geometry_icp":r,"colored_icp":colored,"bad_control_rejected":True,"cleanup":clean,"glb_binary_unchanged":True,"pymeshlab":version("pymeshlab"),"fixture":"synthetic partial overlap, independent controls; no real town model"}
(out/"report.json").write_text(json.dumps(report,indent=2)+"\n");print("MESH_FUSION_QA",json.dumps(report))
