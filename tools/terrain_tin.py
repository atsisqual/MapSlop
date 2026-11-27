"""Offline Delatin adapter. Triangulation is provided by pydelatin, not reimplemented.
The independent barycentric sampler uses the actual exported faces, not a second Delaunay.
"""
import math
from collections import defaultdict
from terrain_grid import ORIGIN, grid_shape

BIN = 16
TIN_SOURCE = {"DGT MDT 0.5 m", "SYNTHETIC TEST TERRAIN"}
INTERNAL_ERROR = 0.25  # leave a margin for off-raster and road samples
VERTEX_LIMIT = 149999

class TinSampler:
    def __init__(self,t):
        self.v=t["vertices"]
        self.f=t["triangles"]
        self.bins=defaultdict(list)
        self.x0=t["x0"];self.z0=t["z0"]
        self.x1=self.x0+(t["nx"]-1)*t["cell"]
        self.z1=self.z0+(t["nz"]-1)*t["cell"]
        for i in range(0,len(self.f),3):
            a,b,c=(3*self.f[i+j] for j in range(3))
            xs=[self.v[j] for j in (a,b,c)]
            zs=[self.v[j+2] for j in (a,b,c)]
            for ix in range(math.floor(min(xs)/BIN),math.floor(max(xs)/BIN)+1):
                for iz in range(math.floor(min(zs)/BIN),math.floor(max(zs)/BIN)+1):
                    self.bins[ix,iz].append((a,b,c))

    def __call__(self,x,z):
        x=max(self.x0,min(self.x1,x));z=max(self.z0,min(self.z1,z))
        v=self.v
        for a,b,c in self.bins.get((math.floor(x/BIN),math.floor(z/BIN)),()):
            dx,dz=v[b]-v[a],v[b+2]-v[a+2]
            ex,ez=v[c]-v[a],v[c+2]-v[a+2]
            det=dx*ez-dz*ex
            u=((x-v[a])*ez-(z-v[a+2])*ex)/det
            w=(dx*(z-v[a+2])-dz*(x-v[a]))/det
            if min(u,w,1-u-w)>=-1e-8:
                return v[a+1]+u*(v[b+1]-v[a+1])+w*(v[c+1]-v[a+1])
        raise ValueError("TIN coverage hole")

def validate_tin(t,bounds=None):
    if t.get("kind")!="tin" or t.get("source") not in TIN_SOURCE or t.get("origin_lat_lon")!=list(ORIGIN):
        raise ValueError("Invalid TIN source or frame")
    if t.get("cell")!=0.5 or (t.get("x0"),t.get("z0"),t.get("nx"),t.get("nz"))!=grid_shape(0.5,bounds):
        raise ValueError("Invalid TIN extent")
    v,f=t.get("vertices",[]),t.get("triangles",[])
    if len(v)%3 or len(f)%3 or not 4<=len(v)//3<=VERTEX_LIMIT or len(f)<6:
        raise ValueError("Invalid TIN topology/vertex budget")
    if not math.isfinite(t["base"]) or any(not isinstance(a,(int,float)) or not math.isfinite(a) for a in v):
        raise ValueError("Nonfinite TIN vertex")
    if any(type(a)!=int or a<0 or a>=len(v)//3 for a in f):
        raise ValueError("Invalid TIN index")
    x0,z0,nx,nz=t["x0"],t["z0"],t["nx"],t["nz"]
    x1,z1=x0+(nx-1)*0.5,z0+(nz-1)*0.5
    if any(not(x0<=v[i]<=x1 and z0<=v[i+2]<=z1 and abs(v[i+1])<9000) for i in range(0,len(v),3)):
        raise ValueError("TIN vertex outside extent")
    area=0.0
    for i in range(0,len(f),3):
        a,b,c=(3*f[i+j] for j in range(3))
        signed=(v[b]-v[a])*(v[c+2]-v[a+2])-(v[b+2]-v[a+2])*(v[c]-v[a])
        if signed>=0:
            raise ValueError("Degenerate or downward-facing TIN face")
        area-=signed/2
    if not math.isclose(area,(x1-x0)*(z1-z0),rel_tol=1e-9,abs_tol=1e-5):
        raise ValueError("TIN area does not match extent")
    return t

def from_raster(heights,x0,z0,base,source,bounds=None):
    """pydelatin emits y-up image coords; convert to row-down world z.
    The half-metre input is sampled directly from the native MDT.
    """
    import numpy as np
    from pydelatin import Delatin
    a=np.ascontiguousarray(heights,dtype=np.float32)
    nz,nx=a.shape
    mesh=Delatin(a,max_error=INTERNAL_ERROR,max_points=VERTEX_LIMIT)
    p=np.asarray(mesh.vertices,dtype=np.float64)
    f=np.asarray(mesh.triangles,dtype=np.int64).copy()
    ix=np.rint(p[:,0]).astype(int)
    iz=nz-1-np.rint(p[:,1]).astype(int)
    if not np.allclose(p[:,2],a[iz,ix],rtol=0,atol=0.002):
        raise ValueError("Delatin image orientation/height mismatch")
    v=np.column_stack((x0+ix*0.5,np.round(p[:,2],3),z0+iz*0.5))
    va,vb,vc=v[f[:,0]],v[f[:,1]],v[f[:,2]]
    signed=(vb[:,0]-va[:,0])*(vc[:,2]-va[:,2])-(vb[:,2]-va[:,2])*(vc[:,0]-va[:,0])
    flip=signed>0
    f[flip]=f[flip][:,[0,2,1]]
    t=dict(kind="tin",source=source,origin_lat_lon=list(ORIGIN),base=round(float(base),3),
           x0=x0,z0=z0,cell=0.5,nx=nx,nz=nz,vertices=v.ravel().tolist(),
           triangles=f.ravel().tolist(),algorithm="pydelatin 0.4.0",
           target_error_m=INTERNAL_ERROR,library_error_m=float(mesh.error))
    return validate_tin(t,bounds)

def refine_roads(t,heights,road_points,road_reference,road_centres,sample_absolute,bounds=None,exact_base=None):
    """Select Delatin vertices, then retriangulate using SciPy/Qhull.
    Fine pass is a candidate pool; retain only vertices <=6 m from OSM axes.
    The final mesh is independently measured, not a constrained breakline mesh.
    """
    import numpy as np
    from scipy.spatial import Delaunay,cKDTree
    from pydelatin import Delatin
    a=np.ascontiguousarray(heights,dtype=np.float32)
    nz,nx=a.shape
    x0,z0=t["x0"],t["z0"]
    x1,z1=x0+(nx-1)*0.5,z0+(nz-1)*0.5
    base=t["base"]
    exact_base=base if exact_base is None else exact_base
    v=np.asarray(t["vertices"],dtype=np.float32).reshape(-1,3)
    xy=v[:,[0,2]].astype(np.float64)
    base_count=len(xy)
    fine=Delatin(a,max_error=0.15,max_points=350000)
    fp=np.asarray(fine.vertices,dtype=np.float64)
    fx=np.rint(fp[:,0]).astype(int)
    fz=nz-1-np.rint(fp[:,1]).astype(int)
    if not np.allclose(fp[:,2],a[fz,fx],rtol=0,atol=0.002):
        raise ValueError("Fine Delatin image orientation mismatch")
    near=np.column_stack((x0+fx*0.5,z0+fz*0.5))
    road_tree=cKDTree(road_centres)
    near=near[road_tree.query(near,k=1)[0]<=6.0]
    near=near[cKDTree(xy).query(near,k=1)[0]>1e-6]
    near=near[np.argsort(road_tree.query(near,k=1)[0],kind="stable")]
    near=near[:max(0,VERTEX_LIMIT-base_count-5000)]
    xy=np.concatenate((xy,near)).astype(np.float32).astype(np.float64)
    y=(sample_absolute(xy[:,0],xy[:,1])-base).astype(np.float32).astype(np.float64)
    corridor_count=len(xy)-base_count
    rounds=[]
    for iteration in range(5):
        tri=Delaunay(xy)
        def interpolate(q):
            idx=tri.find_simplex(q,tol=1e-9)
            if np.any(idx<0):
                raise ValueError("Refined TIN coverage hole")
            b=np.einsum("nij,nj->ni",tri.transform[idx,:2,:],q-tri.transform[idx,2,:])
            w=np.column_stack((b,1-b.sum(axis=1)))
            h=np.einsum("ni,ni->n",w,y[tri.simplices[idx]])
            if not np.all(np.isfinite(h)):
                raise ValueError("Nonfinite refined TIN interpolation")
            return h
        re=np.abs(base+interpolate(road_points)-road_reference)
        raster_max=0.0
        worst_xy=[]
        worst_error=[]
        # Measure every half-metre node of the reprojected MDT in bounded batches.
        for j in range(0,nz,32):
            xx,zz=np.meshgrid(x0+np.arange(nx)*0.5,z0+np.arange(j,min(j+32,nz))*0.5)
            q=np.column_stack((xx.ravel(),zz.ravel()))
            ref=a[j:j+32].astype(np.float64).ravel()+exact_base
            err=np.abs(base+interpolate(q)-ref)
            raster_max=max(raster_max,float(err.max()))
            ids=np.flatnonzero(err>0.43)
            if len(ids):
                ids=ids[np.argsort(-err[ids],kind="stable")[:2000]]
                worst_xy.append(q[ids]);worst_error.append(err[ids])
        rounds.append({"iteration":iteration,"vertices":len(xy),"raster_max_abs_m":raster_max,
                       "road_max_abs_m":float(re.max())})
        if raster_max<=0.5 and float(re.max())<=0.5:
            break
        if iteration==4 or len(xy)>=VERTEX_LIMIT:
            break
        # Insert actual MDT road probes and high-residual raster nodes, within budget.
        ri=np.flatnonzero(re>0.38)
        q=np.concatenate([road_points[ri]]+worst_xy,axis=0)
        err=np.concatenate([re[ri]]+worst_error)
        if not len(q):
            break
        q=np.clip(np.round(q,2),[x0,z0],[x1,z1]).astype(np.float32).astype(np.float64)
        q=q[np.argsort(-err,kind="stable")]
        _,ids=np.unique(q,axis=0,return_index=True)
        q=q[np.sort(ids)]
        q=q[cKDTree(xy).query(q,k=1)[0]>=0.009]
        q=q[:VERTEX_LIMIT-len(xy)]
        if not len(q):
            break
        h=(sample_absolute(q[:,0],q[:,1])-base).astype(np.float32).astype(np.float64)
        xy=np.concatenate((xy,q));y=np.concatenate((y,h))
    f=np.asarray(tri.simplices,dtype=np.int64).copy()
    v=np.column_stack((xy[:,0],y,xy[:,1]))
    va,vb,vc=v[f[:,0]],v[f[:,1]],v[f[:,2]]
    signed=(vb[:,0]-va[:,0])*(vc[:,2]-va[:,2])-(vb[:,2]-va[:,2])*(vc[:,0]-va[:,0])
    f[signed>0]=f[signed>0][:,[0,2,1]]
    result={**t,"vertices":v.ravel().tolist(),"triangles":f.ravel().tolist(),
        "algorithm":"pydelatin 0.4.0 + scipy 1.15.3 Delaunay/Qhull",
        "raster_max_abs_m":raster_max,
        "refinement":{"base_vertices":base_count,"base_delatin_error_m":t["library_error_m"],
            "fine_pool_vertices":len(fp),"fine_pool_error_m":float(fine.error),
            "fine_target_m":0.15,"corridor_radius_m":6.0,"corridor_added_vertices":corridor_count,
            "rounds":rounds,"vertex_limit":VERTEX_LIMIT,"road_target_m":0.5,"raster_samples":int(a.size)}}
    return validate_tin(result,bounds)

def build_tin(mosaic,affine,crs,sample,source="DGT MDT 0.5 m",bounds=None,road_points=None,road_reference=None,road_centres=None):
    import numpy as np
    x0,z0,nx,nz=grid_shape(0.5,bounds)
    base=float(sample(mosaic,affine,crs,np.array([0.0]),np.array([0.0]))[0])
    a=np.empty((nz,nx),dtype=np.float32)
    # Keep transformation buffers bounded rather than materializing millions of Python floats.
    for j in range(0,nz,64):
        x,z=np.meshgrid(x0+np.arange(nx)*0.5,z0+np.arange(j,min(j+64,nz))*0.5)
        a[j:j+64]=sample(mosaic,affine,crs,x,z)-base
    t=from_raster(a,x0,z0,base,source,bounds)
    if road_points is not None:
        return refine_roads(t,a,road_points,road_reference,road_centres,
                            lambda x,z: sample(mosaic,affine,crs,x,z),bounds,exact_base=base)
    return t

def synthetic_tin():
    import numpy as np
    x0,z0,nx,nz=grid_shape(0.5)
    x,z=np.meshgrid(x0+np.arange(nx)*0.5,z0+np.arange(nz)*0.5)
    h=0.035*x+0.025*z+0.3*np.sin(x/45)*np.cos(z/35)
    return from_raster(h,x0,z0,100,"SYNTHETIC TEST TERRAIN")
