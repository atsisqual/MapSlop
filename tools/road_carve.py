"""Offline constrained road carving; one mesh for render and physics."""
import numpy as np
from scipy.spatial import cKDTree
from road_profiles import BERM
from road_surface_policy import RAMP,junction_groups

class Corridor:
    def __init__(self,xy,y,ways,shared_indices=(),groups=None,parallel=None):
        pairs=[];widths=[];self.way_ids=[];self.way_names=[];self.segment_stations=[];self.ways=ways;self.xy=xy;self.y=y
        for w in ways:
            ids=w["ids"]
            pairs.extend(zip(ids,ids[1:]))
            self.segment_stations.extend(range(len(ids)-1))
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
        self.groups=groups if groups is not None else junction_groups(xy,ways,shared_indices)[0]
        self.parallel=parallel
        # Use explicit non-overlapping, mitered station strips to define road heights.
        self.strip_vertices,self.strip_heights,self.strip_triangles=self.make_strips()

    def make_strips(self):
        vertices=[];heights=[];triangles=[]
        for w in self.ways:
            ids=np.asarray(w["ids"]);p=self.xy[ids];h=self.y[ids];half=w["width_m"]/2
            d=np.diff(p,axis=0);d/=np.linalg.norm(d,axis=1)[:,None]
            normal=d[:,::-1]*np.array([-1,1])
            mit=np.vstack([normal[0],normal[:-1]+normal[1:],normal[-1]])
            lengths=np.linalg.norm(mit,axis=1)
            for i in range(1,len(mit)-1):
                if lengths[i]<1e-6:mit[i]=normal[i-1]
                else:mit[i]/=lengths[i]
                factor=max(0.5,float(np.dot(mit[i],normal[i-1])))
                mit[i]/=factor
            start=len(vertices)
            vertices.extend(np.stack([p+half*mit,p-half*mit],axis=1).reshape(-1,2))
            heights.extend(np.repeat(h,2))
            for i in range(len(ids)-1):
                a=start+2*i;b=a+2
                triangles.extend([(a,a+1,b),(b,a+1,b+1)])
        return np.asarray(vertices),np.asarray(heights),np.asarray(triangles,dtype=int)

    def install_strips(self):
        import shapely as sh
        self.strip_polys=sh.polygons(self.strip_vertices[self.strip_triangles])
        self.strip_tree=sh.STRtree(sh.buffer(self.strip_polys,0.012))
        self.platform_polys=sh.buffer(sh.points(self.junction_xy),self.junction_radius,quad_segs=4)
        self.platform_tree=sh.STRtree(sh.buffer(self.platform_polys,0.012))
        self.group_polys=np.asarray([sh.union_all(self.platform_polys[g],grid_size=.01) for g in self.groups],dtype=object)
        self.group_y=np.array([self.junction_y[g[0]] for g in self.groups])
        self.parallel_poly=None
        if self.parallel:
            p=self.parallel
            chosen=np.array([w in p["ways"] for w in self.way_ids]).repeat(2)
            union=sh.union_all(self.strip_polys[chosen],grid_size=.01)
            # Close narrow gaps between the parallel carriageways, not the whole median.
            union=sh.union_all([union,sh.buffer(sh.buffer(union,.6),-.6)],grid_size=.01)
            axis=p["axis"];normal=axis[::-1]*np.array([-1,1])
            def section(lo,hi):
                return sh.Polygon([axis*lo+normal*(-2000),axis*hi+normal*(-2000),axis*hi+normal*2000,axis*lo+normal*2000])
            self.parallel_poly=sh.intersection(union,section(p["lo"],p["hi"]),grid_size=.01)
            self.parallel_lines=[]
            for s in sorted(set([p["lo"],p["hi"],*p["stations"]])):
                if p["lo"]<=s<=p["hi"]:
                    self.parallel_lines.append(sh.intersection(sh.LineString([axis*s-normal*2000,axis*s+normal*2000]),self.parallel_poly,grid_size=.01))

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
        if self.junction_tree is not None and (not platforms or not hasattr(self,'group_polys')):
            d,idx=self.junction_tree.query(q)
            radius=self.junction_radius[idx]
            v=1-np.clip((d-radius)/BERM,0,1) if platforms else 1-np.clip((d-radius*0.5)/np.maximum(radius*0.5,0.01),0,1)
            v=v*v*(3-2*v)
            out=out*(1-v)+self.junction_y[idx]*v
            weights=np.maximum(weights,v)
        if platforms and hasattr(self,"strip_tree"):
            import shapely as sh
            # Paved triangles take precedence over a nearby berm. Barycentric
            # interpolation uses the very same triangles supplied to the CDT.
            points=sh.points(q)
            # Longitudinal station shared by both edges of each mitered cross-section.
            centre_ref=q.copy();half_ref=np.zeros(len(q));strip_assigned=np.zeros(len(q),dtype=bool)
            pp,tt=self.strip_tree.query(points,predicate="intersects")
            choices={}
            for i,j in zip(pp,tt):
                k=j//2
                u=float(np.clip(np.dot(q[i]-self.a[k],self.d[k])/self.length2[k],0,1))
                d=float(np.linalg.norm(q[i]-self.a[k]-u*self.d[k]))
                rank=(d,int(j))
                if i not in choices or rank<choices[i][0]:choices[i]=(rank,j)
            for i,(_,j) in choices.items():
                ids=self.strip_triangles[j];a,b,c=self.strip_vertices[ids]
                d=b-a;e=c-a;v=q[i]-a
                det=d[0]*e[1]-d[1]*e[0]
                if abs(det)<1e-12:continue
                u=(v[0]*e[1]-v[1]*e[0])/det;w=(d[0]*v[1]-d[1]*v[0])/det
                out[i]=(1-u-w)*self.strip_heights[ids[0]]+u*self.strip_heights[ids[1]]+w*self.strip_heights[ids[2]]
                weights[i]=1
                seg=j//2
                fraction=float(np.clip(w if j%2==0 else 1-u,0,1))
                centre_ref[i]=self.a[seg]+fraction*self.d[seg];half_ref[i]=self.half[seg]
                strip_assigned[i]=True
            if self.parallel_poly is not None:
                mask=sh.intersects(sh.buffer(self.parallel_poly,.012),points)
                p=self.parallel
                out[mask]=np.interp(q[mask]@p["axis"],p["stations"],self.y[p["ids"]])
                weights[mask]=1
                # The common cross-section uses the reference lane's centre projected on its axis.
                station=q[mask]@p['axis'];normal=p['axis'][::-1]*np.array([-1,1])
                a=np.interp(station,p['stations'],self.xy[p['ids']]@normal)
                b=np.interp(station,p['other_stations'],self.xy[p['other_ids']]@normal)
                lower=np.minimum(a-p['half_a'],b-p['half_b']);upper=np.maximum(a+p['half_a'],b+p['half_b'])
                centre_ref[mask]=station[:,None]*p['axis']+((lower+upper)*.5)[:,None]*normal
                half_ref[mask]=(upper-lower)*.5
                strip_assigned[mask]=True
            # Apply ramps AFTER assigning the road plane. Each merged core has a
            # single LP height; C1 smoothstep over six metres on the road.
            # Outside the pavement the natural berm remains 2.5m.
            road=weights>=1-1e-9
            centres=sh.points(centre_ref)
            total=np.zeros(len(q));summed=np.zeros(len(q));maxw=np.zeros(len(q))
            for poly,h in zip(self.group_polys,self.group_y):
                dist=sh.distance(poly,points)
                # Start the 6m ramp only once the full cross-section clears the core.
                along=np.maximum(0,sh.distance(poly,centres)-half_ref)
                dist=np.where(strip_assigned,along,dist)
                reach=np.where(road,RAMP,BERM)
                v=1-np.clip(dist/reach,0,1);v=v*v*(3-2*v)
                dominance=v/np.maximum(1-v,1e-9)
                total+=dominance;summed+=dominance*h;maxw=np.maximum(maxw,v)
            mask=total>0
            out[mask]=(1-maxw[mask])*out[mask]+maxw[mask]*summed[mask]/total[mask]
            weights=np.maximum(weights,maxw)
            # No averaging with a different ramp inside a core.
            for poly,h in zip(self.group_polys,self.group_y):
                mask=sh.intersects(sh.buffer(poly,.012),points)
                out[mask]=h;weights[mask]=1
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
    corridor.install_strips()
    platform_shapes=corridor.platform_polys
    shapes=list(corridor.strip_polys)+list(platform_shapes)
    if corridor.parallel_poly is not None:shapes.append(corridor.parallel_poly)
    paved=sh.intersection(sh.union_all(shapes,grid_size=0.01),domain,grid_size=0.01)
    outer=sh.intersection(sh.union_all([envelope(BERM),sh.buffer(paved,BERM,quad_segs=3)],grid_size=0.01),domain,grid_size=0.01)
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
    old_lines=sh.linestrings((original_cm.astype(float)/100)[old_edges])
    sh.prepare(outer)
    hit=sh.intersects(outer,old_lines)
    clipped=sh.difference(old_lines[hit],outer,grid_size=0.01)
    # Node all potentially crossing lines using a centimetre precision model.
    internal=[sh.boundary(paved),sh.boundary(outer),sh.boundary(domain)]
    platform_union=sh.union_all(platform_shapes,grid_size=0.01)
    internal.append(sh.boundary(platform_union))
    # Add node anchors explicitly, and intermediate ramp contours clipped to pavement.
    for p,r in zip(corridor.junction_xy,corridor.junction_radius):
        for d in (np.array([1.,0.]),np.array([0.,1.])):internal.append(sh.LineString([p-d*r*.5,p,p+d*r*.5]))
    for poly in corridor.group_polys:
        # Include inner and outer stations in the paved transition; original strip
        # boundaries already sample cross sections at about 3m.
        for d in (1.5,3.,4.5,6.,9.):
            internal.append(sh.intersection(sh.boundary(sh.buffer(poly,d,quad_segs=3)),paved,grid_size=.01))
    # No redundant axis or cross-section vertices in flat platforms. Strip
    # triangle boundaries preserve longitudinal planes, with no extra midpoints.
    strips=sh.difference(sh.boundary(corridor.strip_polys),platform_union,grid_size=0.01)
    if corridor.parallel_poly is not None:
        strips=sh.difference(strips,corridor.parallel_poly,grid_size=.01)
        internal.append(sh.boundary(corridor.parallel_poly))
        internal.extend(sh.difference(np.asarray(corridor.parallel_lines,dtype=object),platform_union,grid_size=.01))
    internal.extend(strips)
    inside=sh.intersection(np.asarray(internal,dtype=object),domain,grid_size=0.01)
    noded=sh.union_all(np.concatenate([inside,clipped,old_lines[~hit]]),grid_size=0.01)
    points=[];edge_pairs=[]
    def collect(g):
        if g.is_empty:return
        if g.geom_type=="LineString":
            a=np.rint(np.asarray(g.coords)*100).astype(np.int64)
            edge_pairs.extend((tuple(p),tuple(q)) for p,q in zip(a,a[1:]) if not np.array_equal(p,q))
        elif hasattr(g,"geoms"):
            for part in g.geoms:collect(part)
    collect(noded)
    # All exterior edges participated in the same precision-model noding pass.
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
    if not legacy and not hasattr(corridor,'strip_tree'):corridor.install_strips()
    d=corridor.d
    normal=d[:,::-1]*np.array([-1,1]);normal/=np.sqrt(corridor.length2)[:,None]
    centre=(corridor.a+corridor.b)/2
    x0,z0=t["x0"],t["z0"];x1=x0+(t["nx"]-1)*t["cell"];z1=z0+(t["nz"]-1)*t["cell"]
    mask=(centre[:,0]>x0+15)&(centre[:,0]<x1-15)&(centre[:,1]>z0+15)&(centre[:,1]<z1-15)
    # Exclude intersections/overlapping roads from straight transverse check; report how many.
    candidates=np.flatnonzero(mask)
    slopes=[];profile_error=[];all_slopes=[];centre_rows=[];target_errors=[];raw_profile_errors=[];ramp_slopes=[]
    from terrain_grid import ORIGIN,KX,KY
    for i in candidates:
        p=centre[i];half=corridor.half[i]
        junction_distance=float(corridor.junction_tree.query(p)[0]) if corridor.junction_tree is not None else None
        near_junction=junction_distance is not None and junction_distance<2*half
        platform_edge_distance=None
        if not legacy and len(corridor.group_polys):
            import shapely as sh
            platform_edge_distance=float(min(sh.distance(poly,sh.Point(*p)) for poly in corridor.group_polys))
        in_ramp=platform_edge_distance is not None and 0<platform_edge_distance<=RAMP+half
        inside_core=platform_edge_distance==0
        target=float(corridor.target(np.array([p]),np.array([old(*p)]))[0][0])
        target_errors.append(abs(s(*p)-target))
        left=p-normal[i]*half*0.8;right=p+normal[i]*half*0.8
        yl=s(*left);yr=s(*right)
        angle=abs(float(np.degrees(np.arctan2(yr-yl,1.6*half))))
        competitors=[]
        for k in corridor.tree.query_ball_point(p,corridor.search):
            if k==i:continue
            u=float(np.clip(np.dot(p-corridor.a[k],corridor.d[k])/corridor.length2[k],0,1))
            dist=float(np.linalg.norm(p-corridor.a[k]-u*corridor.d[k]))
            if dist<=half+corridor.half[k]:competitors.append({"way":corridor.way_ids[k],"station":corridor.segment_stations[k],"distance_m":dist,"same_way":corridor.way_ids[k]==corridor.way_ids[i],"angle_degrees":float(np.degrees(np.arccos(np.clip(np.dot(corridor.d[k],corridor.d[i])/np.sqrt(corridor.length2[k]*corridor.length2[i]),-1,1))))})
        row={"overlapping_segments":sorted(competitors,key=lambda x:x['distance_m'])[:6],"way":corridor.way_ids[i],"name":corridor.way_names[i],"x_m":float(p[0]),"z_m":float(p[1]),"lat":ORIGIN[0]-float(p[1])/KY,"lon":ORIGIN[1]+float(p[0])/KX,"crossfall_degrees":angle,"junction_distance_m":junction_distance,"near_junction":bool(near_junction),"platform_edge_distance_m":platform_edge_distance,"in_ramp":bool(in_ramp),"inside_platform":bool(inside_core)}
        all_slopes.append(row)
        delta=abs(s(*p)-(corridor.y0[i]+corridor.y1[i])/2)
        raw_profile_errors.append(delta)
        if in_ramp and not near_junction:ramp_slopes.append(row)
        if near_junction:continue
        slopes.append(row)
        if not in_ramp:profile_error.append(delta)
        centre_rows.append({**row,"centre_profile_delta_m":float(delta),"target_delta_m":float(abs(s(*p)-corridor.target(np.array([p]),np.array([old(*p)]))[0][0]))})
    # Check a deterministic set away from the corridor, where a retriangulation may still change the surface.
    xx,zz=np.meshgrid(np.linspace(x0,x1,101),np.linspace(z0,z1,101))
    q=np.column_stack([xx.ravel(),zz.ravel()])
    baseline=np.array([old(*p) for p in q])
    _,w=corridor.target(q,baseline,platforms=not legacy)
    outside=q[w==0];base=baseline[w==0]
    delta=np.abs(np.array([s(*p) for p in outside])-base)
    junction_errors=[abs(s(*p)-h) for p,h in zip(corridor.junction_xy,corridor.junction_y)]
    platform_slopes=[]
    for p,r in zip(corridor.junction_xy,corridor.junction_radius):
        if not (x0+r<p[0]<x1-r and z0+r<p[1]<z1-r):continue
        for axis in (np.array([1.,0.]),np.array([0.,1.])):
            v=axis*r*0.65
            platform_slopes.append(abs(float(np.degrees(np.arctan2(s(*(p+v))-s(*(p-v)),2*r*0.65)))))
    # Additional exterior probes close to the berm, not only on a coarse grid.
    edge_points=[]
    for sign in (-1,1):
        for margin in (0.1,0.5,1.0):
            edge_points.extend(centre+sign*normal*(corridor.half+BERM+margin)[:,None])
    q=np.asarray(edge_points)
    q=q[(q[:,0]>=x0)&(q[:,0]<=x1)&(q[:,1]>=z0)&(q[:,1]<=z1)]
    base=np.array([old(*p) for p in q])
    _,w=corridor.target(q,base,platforms=not legacy)
    q=q[w==0];base=base[w==0]
    edge_delta=np.abs(np.array([s(*p) for p in q])-base)
    return {"junction_samples":len(junction_errors),"max_junction_mesh_delta_m":max(junction_errors,default=0),
            "junction_platform_crossfall_samples":len(platform_slopes),"max_junction_platform_crossfall_degrees":max(platform_slopes,default=None),
            "near_berm_outside_samples":len(edge_delta),"near_berm_outside_max_change_m":float(edge_delta.max(initial=0)),
            "transverse_samples":len(slopes),"max_crossfall_degrees":max((r["crossfall_degrees"] for r in slopes),default=None),
            "worst_10_crossfall":sorted(slopes,key=lambda r:-r["crossfall_degrees"])[:10],
            "all_crossfall_samples":len(all_slopes),"worst_10_all_crossfall":sorted(all_slopes,key=lambda r:-r["crossfall_degrees"])[:10],
            "max_centre_mesh_profile_delta_m":max(raw_profile_errors,default=None),
            "max_centre_mesh_profile_delta_away_from_ramps_m":max(profile_error,default=None),
            "ramp_transverse_samples":len(ramp_slopes),"max_ramp_crossfall_degrees":max((r["crossfall_degrees"] for r in ramp_slopes),default=None),
            "max_centre_mesh_target_delta_m":max(target_errors,default=None),
            "worst_10_centre_delta":sorted(centre_rows,key=lambda r:-r["centre_profile_delta_m"])[:10],
            "outside_samples":len(outside),"outside_max_change_m":float(delta.max(initial=0))}
