#!/usr/bin/env python3
"""Private bounded building cut; original TIN is never modified in place."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import traceback
import numpy as np
import shapely as sh
from shapely.geometry import Polygon,LineString,Point
from terrain_grid import to_world
from terrain_binary import decode,save
from terrain_tin import TinSampler,validate_tin

TARGET=223354671
ORIGINAL_SHA="de37795151e47e5892b4ed8c701968f0bfe60f64f35d9142fc7b89c71ac633d0"
MAX_DEPTH=3.0
RAMP=.60
CLEARANCE=.18

def parts(g,kind):
    if g.is_empty:return []
    if g.geom_type==kind:return [g]
    if hasattr(g,"geoms"):return [p for child in g.geoms for p in parts(child,kind)]
    return []

def polygon(g):
    ps=[p.buffer(0) for p in parts(g,"Polygon") if p.area>1e-8]
    return sh.union_all(ps,grid_size=.01) if ps else Polygon()

def width(t):
    import re
    def num(v):
        m=re.match(r"\s*(\d+(?:\.\d+)?)",str(v or ""))
        return float(m[1]) if m else None
    k=t["highway"].removesuffix("_link")
    lanes=num(t.get("lanes")) or (1 if t["highway"].endswith("_link") else 4 if k in ("motorway","trunk","primary") else 1 if k in ("service","living_street") else 2)
    if not num(t.get("lanes")) and t.get("oneway") in ("yes","1","-1") and lanes>1:lanes/=2
    return num(t.get("width")) or (2.5 if k in ("footway","path","cycleway","steps") else 3.3*lanes+1)

def edge_counts(f):
    return Counter(tuple(sorted((int(a),int(b)))) for row in f for a,b in zip(row,np.roll(row,-1)))

def attempt(t,osm,src,report):
    import pythoncdt as cdt
    old=TinSampler(t)
    verts=np.asarray(t["vertices"],dtype=np.float32).reshape(-1,3)
    xz=np.rint(verts[:,[0,2]].astype(float)*100).astype(np.int64)
    faces=np.asarray(t["triangles"],dtype=np.int64).reshape(-1,3)
    elements=osm["elements"]
    e=next(e for e in elements if e.get("type")=="way" and e["id"]==TARGET)
    def coords(e):return [to_world(p["lon"],p["lat"]) for p in e["geometry"]]
    fp=polygon(Polygon(coords(e)))
    roof=np.asarray(src["roof"],dtype=float).reshape(-1,3,3)
    roofxy=roof[:,:,[0,2]]
    rp=polygon(sh.union_all([Polygon(p) for p in roofxy if Polygon(p).area>1e-8],grid_size=.01))
    if rp.is_empty or not fp.buffer(.35).covers(rp):raise ValueError("Measured roof extends beyond bounded footprint allowance")
    core=polygon(sh.buffer(sh.union_all([fp,rp],grid_size=.01),.05,quad_segs=2))
    outer=polygon(sh.buffer(core,RAMP,quad_segs=2))
    cap=float(roof[:,:,1].min()-CLEARANCE)
    report.update(platform_y_m=cap,core_area_m2=core.area,cut_area_m2=outer.area,transition_m=RAMP,
                  original_roof_min_y_m=float(roof[:,:,1].min()),
                  original_roof_clearance_min_m=min(float(y-old(x,z)) for x,y,z in roof.reshape(-1,3)))
    if report["original_roof_clearance_min_m"]>=.15:
        raise ValueError("Original roof already clears terrain: cut unnecessary")
    if report["original_roof_clearance_min_m"]<-.6:raise ValueError("Intersection exceeds reviewed 0.43 m case")
    # Select whole source faces near the cut; their original perimeter is a hard
    # constraint. Never retriangulate any face outside this local patch.
    mnx,mnz,mxx,mxz=outer.buffer(.05).bounds
    p=xz[faces]/100.
    mask=(p[:,:,0].min(axis=1)<=mxx)&(p[:,:,0].max(axis=1)>=mnx)&(p[:,:,1].min(axis=1)<=mxz)&(p[:,:,1].max(axis=1)>=mnz)
    possible=np.flatnonzero(mask)
    hit=possible[sh.intersects(sh.polygons(p[possible]),outer.buffer(.05))]
    if not len(hit):raise ValueError("No terrain faces for cut")
    patch=polygon(sh.union_all(sh.polygons(p[hit]),grid_size=.01))
    if not patch.covers(outer.buffer(.015)):raise ValueError("Cut not safely inside retriangulated patch")
    report["patch_area_m2"]=patch.area
    if patch.area>400:raise ValueError("Local patch exceeds 400 m2 budget")
    # A patch intersecting any other building or paved corridor is forbidden.
    for obj in elements:
        if obj.get("type")!="way" or obj["id"]==TARGET or len(obj.get("geometry",[]))<2:continue
        tags=obj.get("tags",{})
        if not ("highway" in tags or "building" in tags or "building:part" in tags):continue
        line=LineString(coords(obj))
        if "highway" in tags:
            shape=line.buffer(width(tags)/2+.15)
        elif len(obj["geometry"])>=4:
            shape=Polygon(coords(obj)).buffer(0)
        else:continue
        if patch.intersects(shape):raise ValueError("Local patch touches protected OSM way "+str(obj["id"]))
    ec=edge_counts(faces[hit])
    boundary={edge for edge,n in ec.items() if n==1}
    edges=list(ec)
    ls=sh.linestrings(xz[np.asarray(edges)]/100.)
    noded=sh.union_all([*ls,core.boundary,outer.boundary],grid_size=.01)
    segs=set()
    for line in parts(noded,"LineString"):
        q=np.rint(np.asarray(line.coords)*100).astype(np.int64)
        for a,b in zip(q,q[1:]):
            a,b=tuple(a),tuple(b)
            if a!=b:segs.add(tuple(sorted((a,b))))
    points=sorted({p for edge in segs for p in edge})
    ix={p:i for i,p in enumerate(points)}
    constraints=np.array([(ix[a],ix[b]) for a,b in sorted(segs)],dtype=np.uintc)
    q=np.asarray(points,dtype=float)
    tri=cdt.Triangulation(cdt.VertexInsertionOrder.AUTO,cdt.IntersectingConstraintEdges.NOT_ALLOWED,0.)
    tri.insert_vertices(np.ascontiguousarray(q))
    tri.insert_edges(np.ascontiguousarray(constraints))
    tri.erase_super_triangle()
    vv=tri.vertices_array()
    if not np.array_equal(np.column_stack((vv["x"],vv["y"])),q):raise ValueError("CDT changed local vertices")
    ff=tri.triangles_array()["vertices"].astype(np.int64)
    ff=ff[sh.covers(patch,sh.points(q[ff].mean(axis=1)/100.))]
    actual=edge_counts(ff)
    if any(tuple(sorted(map(int,edge))) not in actual for edge in constraints):
        raise ValueError("Missing local constrained edges")
    new_boundary={tuple(sorted((points[a],points[b]))) for (a,b),n in actual.items() if n==1}
    old_boundary={tuple(sorted((tuple(xz[a]),tuple(xz[b])))) for a,b in boundary}
    if new_boundary!=old_boundary:raise ValueError("Patch perimeter would alter adjacent terrain")
    original_ids={tuple(p):i for i,p in enumerate(xz)}
    v=verts.tolist();mapping=[];depth=0.
    for cm in points:
        x,z=np.asarray(cm)/100.
        idx=original_ids.get(cm)
        natural=float(verts[idx,1]) if idx is not None else old(x,z)
        pt=Point(x,z)
        if core.buffer(.012).covers(pt):weight=1.
        elif outer.covers(pt):weight=max(0.,1.-core.distance(pt)/RAMP)
        else:weight=0.
        weight=weight*weight*(3-2*weight)
        y=natural-weight*max(0.,natural-cap)
        depth=max(depth,natural-y)
        if idx is None:idx=len(v);v.append([x,y,z])
        else:v[idx][1]=y
        mapping.append(idx)
    if depth>MAX_DEPTH:raise ValueError(f"Cut depth {depth:.3f} exceeds {MAX_DEPTH} m")
    report["max_cut_depth_m"]=depth
    mask=np.ones(len(faces),dtype=bool);mask[hit]=False
    ff=np.asarray(mapping,dtype=np.int64)[ff]
    xyz=np.asarray(v,dtype=np.float32)
    a,b,c=xyz[ff[:,0]],xyz[ff[:,1]],xyz[ff[:,2]]
    signed=(b[:,0]-a[:,0])*(c[:,2]-a[:,2])-(b[:,2]-a[:,2])*(c[:,0]-a[:,0])
    if np.any(signed==0):raise ValueError("Degenerate local faces")
    ff[signed>0]=ff[signed>0][:,[0,2,1]]
    # All unchanged outside faces retain their exact original indices/heights.
    outside_ids=np.unique(faces[mask])
    if not np.array_equal(xyz[outside_ids],verts[outside_ids]):raise ValueError("Outside vertices changed")
    candidate={**t,"vertices":xyz.ravel().tolist(),"triangles":np.concatenate([faces[mask],ff]).ravel().tolist()}
    validate_tin(candidate)
    sampler=TinSampler(candidate)
    clearance=min(float(y-sampler(x,z)) for x,y,z in roof.reshape(-1,3))
    # Check entire projected roof against each covering face; a cap below the
    # lowest measured roof is sufficient even between measured vertices.
    for row in ff:
        p3=xyz[row].astype(float)
        face=Polygon(p3[:,[0,2]])
        if not rp.intersects(face):continue
        overlap=rp.intersection(face)
        for g in parts(overlap,"Polygon"):
            for x,z in g.exterior.coords:
                if sampler(x,z)>cap+.015:raise ValueError("Platform cap exceeded below measured roof")
    if clearance<.15:raise ValueError(f"Post-cut clearance {clearance:.3f} below 0.15 m")
    report.update(post_cut_roof_clearance_min_m=clearance,changed_faces=len(hit),
                  replacement_faces=len(ff),added_vertices=len(v)-len(verts),outside_faces_unchanged=int(mask.sum()),
                  outside_vertices_unchanged=len(outside_ids),road_and_neighbour_guard=True)
    return candidate

def main(a):
    root=a.output.parent
    report={"osm_id":TARGET,"status":"not_applied","reason":None,"source_run":46074468277}
    raw=a.terrain.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ORIGINAL_SHA:raise ValueError("Original TIN hash mismatch")
    t=decode(raw)
    src=json.loads(a.roofs.read_text())[str(TARGET)]
    if src.get("policy")!="roofer_lod22_candidate":raise ValueError("Missing measured source roof")
    try:
        new=attempt(t,json.loads(a.osm.read_text()),src,report)
        _,storage=save(a.output,new,compact=True)
        if storage["gzip_bytes"]>=1000000:raise ValueError("Cut TIN exceeds 1 MB gzip")
        report.update(status="applied",storage=storage)
    except Exception as exc:
        traceback.print_exc()
        report.update(status="not_applied",reason=f"{type(exc).__name__}: {exc}")
        shutil.copy2(a.terrain,a.output)
    report["output_sha256"]=hashlib.sha256(a.output.read_bytes()).hexdigest()
    (root/"roof-terrain-cut-report.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print("ROOF_TERRAIN_CUT",json.dumps(report,allow_nan=False),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("terrain","roofs","osm","output"):p.add_argument("--"+name,type=Path,required=True)
    main(p.parse_args())
