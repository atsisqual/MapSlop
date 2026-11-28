"""Reusable robust planar roof envelopes for metric x/y/z samples.
Model selection is data-driven; a separate holdout evaluates the entire pipeline.
No hand-drawn roof heights. Tower segmentation is a geometric proxy, not a survey.
"""
import math
import numpy as np
import shapely as sh
from shapely.geometry import Polygon, box
from shapely.ops import transform
from scipy.optimize import least_squares
from scipy.spatial import cKDTree
from scipy.sparse.csgraph import connected_components

def axis_frame(p):
    r=np.asarray(p.minimum_rotated_rectangle.exterior.coords)[:4]
    d=np.roll(r,-1,axis=0)-r;i=int(np.argmax(np.linalg.norm(d,axis=1)))
    u=d[i]/np.linalg.norm(d[i])
    if u[0]<0:u=-u
    v=np.array([-u[1],u[0]])
    return np.stack((u,v),axis=1)

def partition_tower(p,q):
    """Look for a connected upper tier, snap its orthogonal envelope to nearby footprint vertices."""
    y=q[:,2];level=max(float(np.median(y)+3.5),float(np.quantile(y,.8)+1.0))
    top=q[y>level]
    if len(top)<25:return None
    g=cKDTree(top[:,:2]).sparse_distance_matrix(cKDTree(top[:,:2]),1.15,output_type="coo_matrix")
    _,labels=connected_components(g.tocsr(),directed=False)
    group=top[labels==np.argmax(np.bincount(labels))]
    if len(group)<25:return None
    lo=np.quantile(group[:,:2],.01,axis=0)-.25;hi=np.quantile(group[:,:2],.99,axis=0)+.25
    vertices=np.asarray(p.exterior.coords)
    for j in range(2):
        for val in (lo,hi):
            nearest=vertices[np.argmin(np.abs(vertices[:,j]-val[j])),j]
            if abs(nearest-val[j])<=1.0:val[j]=nearest
    tower=p.intersection(box(*lo,*hi))
    if tower.geom_type!="Polygon" or not 8<=tower.area<=p.area*.38:return None
    if p.difference(tower).area<p.area*.6:return None
    return tower

def plane_fit(q,region):
    """Candidate flat/shed/gable/hip continuous lower envelopes, robust soft-L1 fitting.
    Each row is [du,dv,intercept]. An envelope is clipped at exact plane intersections.
    """
    x=q[:,:2];y=q[:,2];mid=x.mean(axis=0);z=x-mid
    if len(q)<12:raise ValueError("Too few samples for plane fit")
    base=float(np.median(y));hi=float(np.quantile(y,.95));scale=max(1.,float(np.ptp(y)))
    # Unconstrained constant/sloped plane, then opposite-sign axis slope pairs.
    directions=[np.array([[0.,0.]]),np.array([[1.,0.],[-1.,0.]]),np.array([[0.,1.],[0.,-1.]]),np.array([[1.,0.],[-1.,0.],[0.,1.],[0.,-1.]])]
    candidates=[]
    A=np.column_stack((z,np.ones(len(z))))
    r=least_squares(lambda b:A@b-y,np.array([0.,0.,base]),loss="soft_l1",f_scale=.3,bounds=([-1.5,-1.5,base-2*scale],[1.5,1.5,base+2*scale]))
    b=r.x.copy();b[2]-=b[:2]@mid
    candidates.append(("shed",b[None,:]))
    for dirs in directions:
        n=len(dirs);init=np.r_[np.full(n,.40 if n>1 else 0.),np.full(n,hi)]
        def pred(a):return np.min(z@((dirs*a[:n,None]).T)+a[n:],axis=1)
        res=least_squares(lambda a:pred(a)-y,init,bounds=(np.r_[np.zeros(n),np.full(n,base-2*scale-5)],np.r_[np.full(n,2.),np.full(n,hi+3*scale+5)]),loss="soft_l1",f_scale=.3,max_nfev=160)
        slopes=dirs*res.x[:n,None];planes=np.column_stack((slopes,res.x[n:]-slopes@mid))
        candidates.append(({1:"flat",2:"gable",4:"hip"}[n],planes))
    scored=[]
    for name,b in candidates:
        predicted=np.min(x@b[:,:2].T+b[:,2],axis=1);err=predicted-y
        # Robust residual with mild preference for fewer active planes.
        loss=float(np.mean(np.sqrt(err*err+.3**2)-.3))+.018*len(b)
        scored.append((loss,name,b))
    _,name,b=min(scored,key=lambda x:x[0])
    return name,b

def clip_halfplane(poly,d):
    """Intersect with du*u+dv*v+c <= 0, via a finite convex halfplane polygon."""
    a,b,c=map(float,d);norm=math.hypot(a,b)
    if norm<1e-10:return poly if c<=1e-8 else Polygon()
    n=np.array([a,b])/norm;t=np.array([-n[1],n[0]]);on=-c/norm*n
    bounds=np.asarray(poly.bounds);extent=max(100.,float(np.max(np.abs(bounds)))+float(np.linalg.norm(on))+100.)
    hp=Polygon([on-t*extent,on+t*extent,on+t*extent-n*2*extent,on-t*extent-n*2*extent])
    return poly.intersection(hp)

def fit(p,samples,detect_tower=True):
    basis=axis_frame(p)
    def local(x,z,h=None):return (np.asarray(x)*basis[0,0]+np.asarray(z)*basis[1,0],np.asarray(x)*basis[0,1]+np.asarray(z)*basis[1,1])
    def world(u,v,h=None):return (np.asarray(u)*basis[0,0]+np.asarray(v)*basis[0,1],np.asarray(u)*basis[1,0]+np.asarray(v)*basis[1,1])
    region=transform(local,p);xy=samples[:,[0,2]]@basis;q=np.column_stack((xy,samples[:,1]))
    tower=partition_tower(region,q) if detect_tower else None
    shapes=[("nave",region)] if tower is None else [("nave",region.difference(tower)),("tower",tower)]
    models=[]
    for name,poly in shapes:
        hit=sh.intersects_xy(poly,q[:,0],q[:,1])
        if name=="nave" and tower is not None:hit&=~sh.intersects_xy(tower,q[:,0],q[:,1])
        kind,planes=plane_fit(q[hit],poly)
        models.append((name,poly,kind,planes,int(hit.sum())))
    def local_height(u,v):
        from shapely.geometry import Point
        point=Point(u,v)
        # On a shared tower edge, prefer the upper tier. Other models are continuous.
        for name,poly,kind,planes,count in reversed(models):
            if poly.distance(point)<=1e-7:return float(np.min(planes[:,:2]@[u,v]+planes[:,2]))
        name,poly,kind,planes,count=min(models,key=lambda m:m[1].distance(point))
        return float(np.min(planes[:,:2]@[u,v]+planes[:,2]))
    def height(x,z):
        u,v=local(x,z);return local_height(u,v)
    return basis,models,local,world,height

def mesh_planar(p,samples,ground):
    basis,models,local,world,height=fit(p,samples)
    roofs=[];walls=[];regions=[];support=[];area=0.
    tree=cKDTree(samples[:,[0,2]])
    for name,region,kind,planes,count in models:
        facets=[]
        for i,plane in enumerate(planes):
            poly=region
            for j,other in enumerate(planes):
                if j!=i and not poly.is_empty:
                    diff=plane-other
                    if np.linalg.norm(diff)<1e-9:
                        if j<i:poly=Polygon()
                    else:poly=clip_halfplane(poly,diff)
            for piece in sh.get_parts(poly):
                if piece.geom_type!="Polygon" or piece.area<1e-6:continue
                def xyz(u,v):
                    x,z=world(u,v);y=float(plane@[u,v,1.])
                    if y-ground(float(x),float(z))<1:raise ValueError("Fitted roof intersects ground")
                    return (float(x),y,float(z))
                for tri in sh.get_parts(sh.constrained_delaunay_triangles(piece)):
                    if tri.area<1e-7:continue
                    coords=list(tri.exterior.coords)[:3];a,b,c=np.asarray(coords)
                    if np.cross(b-a,c-a)>0:coords.reverse()
                    verts=[xyz(*q) for q in coords];roofs.append(verts);area+=tri.area
                    for x,y,z in verts:support.append(float(tree.query([x,z])[0]))
                # Only region edges, not internal roof plane boundaries. Split on exact plane intersection.
                from shapely.geometry import LineString
                for ring in [piece.exterior,*piece.interiors]:
                    coords=list(ring.coords)
                    for a,b in zip(coords,coords[1:]):
                        seg=LineString([a,b])
                        if seg.length<1e-5 or seg.difference(region.boundary.buffer(1e-6)).length>1e-5:continue
                        at,bt=xyz(*a),xyz(*b)
                        # Outer shell follows actual footprint; tower wall spans to base (hidden below nave).
                        if name!="tower" and seg.difference(transform(local,p).boundary.buffer(1e-6)).length>1e-5:continue
                        n=max(1,math.ceil(seg.length/.5))
                        for k in range(n):
                            A=np.array(a)+(np.array(b)-a)*(k/n);B=np.array(a)+(np.array(b)-a)*((k+1)/n)
                            A=xyz(*A);B=xyz(*B)
                            ab=(A[0],ground(A[0],A[2])-.02,A[2]);bb=(B[0],ground(B[0],B[2])-.02,B[2])
                            walls.extend([[ab,bb,B],[ab,B,A]])
                facets.append({"plane":plane.tolist(),"area_m2":float(piece.area)})
        regions.append({"name":name,"kind":kind,"sample_count":count,"area_m2":float(region.area),"facets":facets})
    if abs(area-p.area)>max(.01,p.area*1e-5):raise ValueError(f"Plane coverage mismatch: {area} vs {p.area}")
    return roofs,walls,np.asarray(support),area,height,regions
