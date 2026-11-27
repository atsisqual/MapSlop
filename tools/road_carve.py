"""Experimental offline road carving. One output TIN for all existing render/physics paths.
Unconstrained Delaunay is NOT a guarantee of exact road breaklines: measure decoded mesh.
"""
import numpy as np
from scipy.spatial import cKDTree, Delaunay
from road_profiles import BERM

class Corridor:
    def __init__(self,xy,y,ways,shared_indices=()):
        pairs=[];widths=[]
        for w in ways:
            ids=w["ids"]
            pairs.extend(zip(ids,ids[1:]))
            widths.extend([w["width_m"]/2]*(len(ids)-1))
        pairs=np.asarray(pairs,dtype=int)
        self.a=xy[pairs[:,0]];self.b=xy[pairs[:,1]]
        self.d=self.b-self.a
        self.length2=np.sum(self.d*self.d,axis=1)
        self.y0=y[pairs[:,0]];self.y1=y[pairs[:,1]]
        self.half=np.asarray(widths)
        self.tree=cKDTree((self.a+self.b)/2)
        self.search=float(self.half.max()+BERM+np.sqrt(self.length2.max())/2)
        self.junction_xy=xy[np.asarray(shared_indices,dtype=int)]
        self.junction_y=y[np.asarray(shared_indices,dtype=int)]
        radii={}
        for w in ways:
            for i in w["ids"]:
                radii[i]=max(radii.get(i,0),w["width_m"]/2)
        self.junction_radius=np.array([radii[i] for i in shared_indices])
        self.junction_tree=cKDTree(self.junction_xy) if len(self.junction_xy) else None

    def target(self,q,natural):
        out=np.asarray(natural,dtype=float).copy();weights=np.zeros(len(q))
        for i,indices in enumerate(self.tree.query_ball_point(q,self.search)):
            if not indices:continue
            k=np.asarray(indices)
            u=np.clip(np.sum((q[i]-self.a[k])*self.d[k],axis=1)/self.length2[k],0,1)
            d=np.linalg.norm(q[i]-self.a[k]-u[:,None]*self.d[k],axis=1)
            edge=d-self.half[k]
            # Prefer nearest centreline inside road; outside, nearest paved edge.
            j=np.lexsort((k,d,np.maximum(edge,0)))[0]
            blend=1-np.clip(edge[j]/BERM,0,1)
            blend=blend*blend*(3-2*blend)
            height=self.y0[k[j]]+u[j]*(self.y1[k[j]]-self.y0[k[j]])
            out[i]=natural[i]+blend*(height-natural[i]);weights[i]=blend
        # Blend toward the single common junction elevation inside its footprint.
        if self.junction_tree is not None:
            d,idx=self.junction_tree.query(q)
            radius=self.junction_radius[idx]
            v=1-np.clip((d-radius*0.5)/np.maximum(radius*0.5,0.01),0,1)
            v=v*v*(3-2*v)
            out=out*(1-v)+self.junction_y[idx]*v
            weights=np.maximum(weights,v)
        return out,weights

    def cross_points(self):
        normal=self.d[:,::-1]*np.array([-1,1])
        normal/=np.sqrt(self.length2)[:,None]
        # Control samples at centre, paved edges and berm limits, both endpoints and midpoint.
        samples=[]
        for u in (0,0.5,1):
            p=self.a+u*self.d
            for f in (-1,0,1):
                samples.append(p+normal*(f*self.half)[:,None])
                if f:samples.append(p+normal*(f*(self.half+BERM))[:,None])
        return np.concatenate(samples)

def deform(t,corridor):
    from terrain_tin import TinSampler,validate_tin,VERTEX_LIMIT
    v=np.array(t["vertices"],dtype=np.float32).reshape(-1,3)
    original=v[:,[0,2]].astype(float)
    # Avoid changing x/z of existing vertices, including the centimetre control points.
    points=corridor.cross_points()
    x0,z0=t["x0"],t["z0"]
    x1,z1=x0+(t["nx"]-1)*t["cell"],z0+(t["nz"]-1)*t["cell"]
    points=np.clip(np.round(points,2),[x0,z0],[x1,z1]).astype(np.float32).astype(float)
    points=np.unique(points,axis=0)
    points=points[cKDTree(original).query(points)[0]>=0.009]
    if len(original)+len(points)>VERTEX_LIMIT:
        raise ValueError(f"Road control points exceed TIN budget: {len(original)+len(points)}")
    sampler=TinSampler(t)
    heights=np.r_[v[:,1].astype(float),[sampler(float(x),float(z)) for x,z in points]]
    xy=np.vstack([original,points])
    y,weights=corridor.target(xy,heights)
    tri=Delaunay(xy).simplices.copy()
    vv=np.column_stack([xy[:,0],y,xy[:,1]]).astype(np.float32)
    a,b,c=vv[tri[:,0]],vv[tri[:,1]],vv[tri[:,2]]
    signed=(b[:,0]-a[:,0])*(c[:,2]-a[:,2])-(b[:,2]-a[:,2])*(c[:,0]-a[:,0])
    tri[signed>0]=tri[signed>0][:,[0,2,1]]
    # The old refinement metadata no longer describes this changed geometry.
    out={k:v for k,v in t.items() if k not in ("raster_max_abs_m","refinement","library_error_m","target_error_m")}
    out.update(vertices=vv.ravel().tolist(),triangles=tri.ravel().tolist(),
               algorithm="experimental road-carve Delaunay",road_carve=True)
    return validate_tin(out),{"added_vertices":len(points),"vertices_changed":int(np.count_nonzero(np.abs(y-heights)>1e-6)),
                              "max_vertex_shift_m":float(np.max(np.abs(y-heights))),
                              "unchanged_outside_vertex_count":int(np.count_nonzero(weights==0))}

def check_surface(t,original,corridor):
    from terrain_tin import TinSampler
    s=TinSampler(t);old=TinSampler(original)
    d=corridor.d
    normal=d[:,::-1]*np.array([-1,1]);normal/=np.sqrt(corridor.length2)[:,None]
    centre=(corridor.a+corridor.b)/2
    x0,z0=t["x0"],t["z0"];x1=x0+(t["nx"]-1)*t["cell"];z1=z0+(t["nz"]-1)*t["cell"]
    mask=(centre[:,0]>x0+15)&(centre[:,0]<x1-15)&(centre[:,1]>z0+15)&(centre[:,1]<z1-15)
    # Exclude intersections/overlapping roads from straight transverse check; report how many.
    candidates=np.flatnonzero(mask)
    slopes=[];profile_error=[]
    for i in candidates:
        p=centre[i];half=corridor.half[i]
        if corridor.junction_tree is not None and corridor.junction_tree.query(p)[0]<2*half:continue
        left=p-normal[i]*half*0.8;right=p+normal[i]*half*0.8
        yl=s(*left);yr=s(*right)
        slopes.append(abs(float(np.degrees(np.arctan2(yr-yl,1.6*half)))))
        profile_error.append(abs(s(*p)-(corridor.y0[i]+corridor.y1[i])/2))
    # Check a deterministic set away from the corridor, where a retriangulation may still change the surface.
    xx,zz=np.meshgrid(np.linspace(x0,x1,101),np.linspace(z0,z1,101))
    q=np.column_stack([xx.ravel(),zz.ravel()])
    baseline=np.array([old(*p) for p in q])
    _,w=corridor.target(q,baseline)
    outside=q[w==0];base=baseline[w==0]
    delta=np.abs(np.array([s(*p) for p in outside])-base)
    return {"transverse_samples":len(slopes),"max_crossfall_degrees":max(slopes,default=None),
            "max_centre_mesh_profile_delta_m":max(profile_error,default=None),
            "outside_samples":len(outside),"outside_max_change_m":float(delta.max(initial=0))}
