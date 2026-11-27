"""Offline constrained road carving; one mesh for render and physics."""
import numpy as np
from scipy.spatial import cKDTree
from road_profiles import BERM

class Corridor:
    def __init__(self,xy,y,ways,shared_indices=()):
        pairs=[];widths=[];self.way_ids=[];self.way_names=[]
        for w in ways:
            ids=w["ids"]
            pairs.extend(zip(ids,ids[1:]))
            widths.extend([w["width_m"]/2]*(len(ids)-1))
            self.way_ids.extend([w.get("way")]*(len(ids)-1));self.way_names.extend([w.get("name")]*(len(ids)-1))
        pairs=np.asarray(pairs,dtype=int)
        self.a=xy[pairs[:,0]];self.b=xy[pairs[:,1]]
        self.d=self.b-self.a
        self.length2=np.sum(self.d*self.d,axis=1)
        self.y0=y[pairs[:,0]];self.y1=y[pairs[:,1]]
        self.half=np.asarray(widths)
        self.tree=cKDTree((self.a+self.b)/2)
        self.search=float(self.half.max()+BERM+np.sqrt(self.length2.max())/2)
        self.junction_indices=list(shared_indices)
        self.junction_xy=xy[np.asarray(shared_indices,dtype=int)]
        self.junction_y=y[np.asarray(shared_indices,dtype=int)]
        radii={}
        for w in ways:
            for i in w["ids"]:
                radii[i]=max(radii.get(i,0),w["width_m"]/2)
        self.junction_radius=np.array([radii[i] for i in shared_indices])
        self.junction_tree=cKDTree(self.junction_xy) if len(self.junction_xy) else None

    def target(self,q,natural,platforms=True):
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
            v=1-np.clip((d-radius)/BERM,0,1) if platforms else 1-np.clip((d-radius*0.5)/np.maximum(radius*0.5,0.01),0,1)
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

def constrained_mesh(points,edges):
    import pythoncdt as cdt
    # Integer centimetres are exactly representable in double precision.
    vertices=np.ascontiguousarray(points,dtype=np.float64)
    edges=np.ascontiguousarray(edges,dtype=np.uintc)
    tr=cdt.Triangulation(cdt.VertexInsertionOrder.AUTO,
                         cdt.IntersectingConstraintEdges.NOT_ALLOWED,0.0)
    tr.insert_vertices(vertices)
    tr.insert_edges(edges)
    tr.erase_super_triangle()
    vv=tr.vertices_array()
    xy=np.column_stack((vv["x"],vv["y"]))
    faces=tr.triangles_array()["vertices"].astype(np.int64)
    if not np.array_equal(xy,vertices):raise ValueError("CDT changed vertex identities/coordinates")
    # Every input constraint must survive as an edge, or an exact chain of collinear edges.
    mesh_edges={tuple(sorted((int(a),int(b)))) for f in faces for a,b in zip(f,np.roll(f,-1))}
    adjacency={}
    for a,b in mesh_edges:
        adjacency.setdefault(a,[]).append(b);adjacency.setdefault(b,[]).append(a)
    missing=[]
    for a,b in edges:
        a,b=int(a),int(b)
        if tuple(sorted((a,b))) in mesh_edges:continue
        p,q=points[a],points[b];d=q-p
        cur=a;seen={a}
        while cur!=b:
            candidates=[]
            for j in adjacency.get(cur,[]):
                v=points[j]-p
                if j not in seen and d[0]*v[1]==d[1]*v[0] and 0<=np.dot(v,d)<=np.dot(d,d):
                    candidates.append(j)
            if not candidates:break
            cur=max(candidates,key=lambda j:np.dot(points[j]-p,d));seen.add(cur)
        if cur!=b:missing.append((a,b))
    if missing:raise ValueError(f"CDT missing mandatory edge chains: {len(missing)}")
    return faces,{"mandatory_edges":len(edges),"missing_mandatory_edges":0}

def deform(t,corridor):
    import shapely as sh
    from shapely.geometry import LineString,Point,box
    from terrain_tin import TinSampler,validate_tin,VERTEX_LIMIT
    v=np.array(t["vertices"],dtype=np.float32).reshape(-1,3)
    original=v[:,[0,2]].astype(float)
    original_cm=np.rint(original*100).astype(np.int64)
    x0,z0=t["x0"],t["z0"]
    x1,z1=x0+(t["nx"]-1)*t["cell"],z0+(t["nz"]-1)*t["cell"]
    domain=box(x0,z0,x1,z1)
    # Polygon union gives actual exterior paved/berm boundaries at intersections.
    # Round caps at the segment ends match the projection rule of Corridor.target.
    axes=sh.linestrings(np.stack([corridor.a,corridor.b],axis=1))
    def envelope(extra):
        segments=sh.buffer(axes,corridor.half+extra,quad_segs=3)
        platforms=sh.buffer(sh.points(corridor.junction_xy),corridor.junction_radius+extra,quad_segs=4)
        return sh.intersection(sh.union_all(np.concatenate([segments,platforms]),grid_size=0.01),domain,grid_size=0.01)
    paved=envelope(0);outer=envelope(BERM)
    platform_shapes=sh.buffer(sh.points(corridor.junction_xy),corridor.junction_radius,quad_segs=4)
    # Split at stations with transverse lines; no additional midpoint fan or duplicate original interior samples.
    normal=corridor.d[:,::-1]*np.array([-1,1]);normal/=np.sqrt(corridor.length2)[:,None]
    cross=[]
    for p in (corridor.a,corridor.b):
        left=p-normal*corridor.half[:,None];right=p+normal*corridor.half[:,None]
        cross.extend(sh.linestrings(np.stack([left,right],axis=1)))
    # Keep mandatory ORIGINAL edge segments outside the outer berm, preserving
    # the old piecewise planar terrain; split only intersecting edges at the boundary.
    faces=np.asarray(t["triangles"],dtype=int).reshape(-1,3)
    old_edges=np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
    old_lines=sh.linestrings(original[old_edges])
    sh.prepare(outer)
    hit=sh.intersects(outer,old_lines)
    clipped=sh.difference(old_lines[hit],outer,grid_size=0.01)
    # Node all potentially crossing lines using a centimetre precision model.
    internal=[sh.boundary(paved),sh.boundary(outer),sh.boundary(domain)]
    internal.extend(sh.boundary(platform_shapes))
    internal.extend(axes);internal.extend(cross)
    inside=sh.intersection(np.asarray(internal,dtype=object),domain,grid_size=0.01)
    noded=sh.union_all(np.concatenate([inside,clipped]),grid_size=0.01)
    points=[];edge_pairs=[]
    def collect(g):
        if g.is_empty:return
        if g.geom_type=="LineString":
            a=np.rint(np.asarray(g.coords)*100).astype(np.int64)
            edge_pairs.extend((tuple(p),tuple(q)) for p,q in zip(a,a[1:]) if not np.array_equal(p,q))
        elif hasattr(g,"geoms"):
            for part in g.geoms:collect(part)
    collect(noded)
    # Exterior edges never intersect internal constraints except where noding
    # already split an incident clipped edge; their endpoint grid is unchanged.
    for a,b in old_edges[~hit]:
        edge_pairs.append((tuple(original_cm[a]),tuple(original_cm[b])))
    coords=sorted({p for pair in edge_pairs for p in pair})
    lookup={p:i for i,p in enumerate(coords)}
    edges=np.array(sorted({tuple(sorted((lookup[a],lookup[b]))) for a,b in edge_pairs}),dtype=np.int64)
    cm=np.asarray(coords,dtype=np.int64)
    if len(cm)>VERTEX_LIMIT:raise ValueError(f"CDT vertex budget exceeded: {len(cm)}")
    tri,proof=constrained_mesh(cm,edges)
    xy=cm.astype(float)/100
    sampler=TinSampler(t)
    original_lookup={tuple(p):float(h) for p,h in zip(original_cm,v[:,1])}
    heights=np.array([original_lookup[p] if p in original_lookup else sampler(*q) for p,q in zip(coords,xy)])
    y,weights=corridor.target(xy,heights)
    vv=np.column_stack([xy[:,0],y,xy[:,1]]).astype(np.float32)
    a,b,c=vv[tri[:,0]],vv[tri[:,1]],vv[tri[:,2]]
    signed=(b[:,0]-a[:,0])*(c[:,2]-a[:,2])-(b[:,2]-a[:,2])*(c[:,0]-a[:,0])
    tri[signed>0]=tri[signed>0][:,[0,2,1]]
    out={k:v for k,v in t.items() if k not in ("raster_max_abs_m","refinement","library_error_m","target_error_m")}
    out.update(vertices=vv.ravel().tolist(),triangles=tri.ravel().tolist(),algorithm="PythonCDT 2.1.1 constrained road carve",road_carve=True)
    kept=sum(p in original_lookup for p in coords)
    return validate_tin(out),{**proof,"added_vertices":len(cm)-kept,"removed_original_vertices":len(original)-kept,
        "vertices":len(cm),"vertices_changed":int(np.count_nonzero(np.abs(y-heights)>1e-6)),
        "max_vertex_shift_m":float(np.max(np.abs(y-heights))),"unchanged_outside_vertex_count":int(np.count_nonzero(weights==0)),
        "platform_count":len(corridor.junction_xy),"paved_area_m2":float(paved.area),"berm_envelope_area_m2":float(outer.area)}

def check_surface(t,original,corridor,legacy=False):
    from terrain_tin import TinSampler
    s=TinSampler(t);old=TinSampler(original)
    d=corridor.d
    normal=d[:,::-1]*np.array([-1,1]);normal/=np.sqrt(corridor.length2)[:,None]
    centre=(corridor.a+corridor.b)/2
    x0,z0=t["x0"],t["z0"];x1=x0+(t["nx"]-1)*t["cell"];z1=z0+(t["nz"]-1)*t["cell"]
    mask=(centre[:,0]>x0+15)&(centre[:,0]<x1-15)&(centre[:,1]>z0+15)&(centre[:,1]<z1-15)
    # Exclude intersections/overlapping roads from straight transverse check; report how many.
    candidates=np.flatnonzero(mask)
    slopes=[];profile_error=[];all_slopes=[]
    from terrain_grid import ORIGIN,KX,KY
    for i in candidates:
        p=centre[i];half=corridor.half[i]
        junction_distance=float(corridor.junction_tree.query(p)[0]) if corridor.junction_tree is not None else None
        near_junction=junction_distance is not None and junction_distance<2*half
        left=p-normal[i]*half*0.8;right=p+normal[i]*half*0.8
        yl=s(*left);yr=s(*right)
        angle=abs(float(np.degrees(np.arctan2(yr-yl,1.6*half))))
        row={"way":corridor.way_ids[i],"name":corridor.way_names[i],"x_m":float(p[0]),"z_m":float(p[1]),"lat":ORIGIN[0]-float(p[1])/KY,"lon":ORIGIN[1]+float(p[0])/KX,"crossfall_degrees":angle,"junction_distance_m":junction_distance,"near_junction":bool(near_junction)}
        all_slopes.append(row)
        if near_junction:continue
        slopes.append(row)
        profile_error.append(abs(s(*p)-(corridor.y0[i]+corridor.y1[i])/2))
    # Check a deterministic set away from the corridor, where a retriangulation may still change the surface.
    xx,zz=np.meshgrid(np.linspace(x0,x1,101),np.linspace(z0,z1,101))
    q=np.column_stack([xx.ravel(),zz.ravel()])
    baseline=np.array([old(*p) for p in q])
    _,w=corridor.target(q,baseline,platforms=not legacy)
    outside=q[w==0];base=baseline[w==0]
    delta=np.abs(np.array([s(*p) for p in outside])-base)
    junction_errors=[abs(s(*p)-h) for p,h in zip(corridor.junction_xy,corridor.junction_y)]
    return {"junction_samples":len(junction_errors),"max_junction_mesh_delta_m":max(junction_errors,default=0),
            "transverse_samples":len(slopes),"max_crossfall_degrees":max((r["crossfall_degrees"] for r in slopes),default=None),
            "worst_10_crossfall":sorted(slopes,key=lambda r:-r["crossfall_degrees"])[:10],
            "all_crossfall_samples":len(all_slopes),"worst_10_all_crossfall":sorted(all_slopes,key=lambda r:-r["crossfall_degrees"])[:10],
            "max_centre_mesh_profile_delta_m":max(profile_error,default=None),
            "outside_samples":len(outside),"outside_max_change_m":float(delta.max(initial=0))}
