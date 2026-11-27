"""Independent offline road profiles, no PortoSlop code/data.
The LP minimizes maximum deviation, then sum of deviations, under grade-change constraints.
"""
import math
from collections import Counter
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
from terrain_grid import to_world

STEP=3.0
CURVATURE=0.02/3
MAX_DEVIATION=0.5
BERM=2.5
KINDS={"motorway","trunk","primary","secondary","tertiary","unclassified","residential","living_street","service"}

def eligible(e):
    t=e.get("tags",{})
    return e.get("type")=="way" and t.get("highway","").removesuffix("_link") in KINDS and t.get("area")!="yes" and t.get("access")!="private"

def structural(t):
    return [k for k in ("bridge","tunnel","embankment","cutting") if t.get(k,"no") not in ("no","0","")] + (["layer"] if t.get("layer","0")!="0" else [])

def road_width(t):
    # Same width rules as the pinned upstream, independent of the profile solver.
    kind=t["highway"].removesuffix("_link")
    def number(x):
        import re
        m=re.match(r"\s*(-?\d+(?:\.\d+)?)",str(x or ""))
        return float(m[1]) if m else None
    width=number(t.get("width"))
    lanes=number(t.get("lanes"))
    defaults=4 if kind in ("motorway","trunk","primary") else 1 if kind in ("living_street","service") else 2
    one=t.get("oneway") in ("yes","1","-1") or t.get("junction")=="roundabout" or (kind=="motorway" and t.get("oneway")!="no")
    lanes=lanes or (1 if t["highway"].endswith("_link") else defaults/(2 if one and defaults>1 else 1))
    return width or max(lanes,1)*3.3+(0 if kind=="service" else 1)

def network(osm):
    roads=[e for e in osm["elements"] if eligible(e)]
    excluded=[]; valid=[]
    for e in roads:
        tags=e["tags"];why=structural(tags)
        if why:
            excluded.append({"way":e["id"],"name":tags.get("name"),"reason":why})
            continue
        if len(e.get("nodes",[]))!=len(e.get("geometry",[])) or len(e["nodes"])<2:
            raise ValueError("Missing geometry/node identities")
        valid.append(e)
    counts=Counter(n for e in valid for n in set(e["nodes"]))
    # Endpoints and nodes shared between distinct ways get exact common variables.
    shared={n for n,c in counts.items() if c>1}
    xy=[];node_index={};ways=[]
    def point(p,node=None):
        if node is not None and node in node_index:
            i=node_index[node]
            if np.linalg.norm(np.array(xy[i])-p)>0.02:raise ValueError("Conflicting OSM node positions")
            return i
        i=len(xy);xy.append(tuple(p))
        if node is not None:node_index[node]=i
        return i
    for e in valid:
        coords=np.array([to_world(p["lon"],p["lat"]) for p in e["geometry"]])
        nodes=e["nodes"]
        breaks=[i for i,n in enumerate(nodes) if i in (0,len(nodes)-1) or n in shared]
        ids=[];dist=[]
        for a,b in zip(breaks,breaks[1:]):
            p=coords[a:b+1]
            s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
            if s[-1]<1e-6:continue
            samples=np.linspace(0,s[-1],max(1,math.ceil(s[-1]/STEP))+1)
            # Preserve sharp geometry vertices without introducing a second height at junctions.
            pos=np.column_stack([np.interp(samples,s,p[:,k]) for k in range(2)])
            for j,q in enumerate(pos):
                if ids and j==0:continue
                n=nodes[a] if j==0 else nodes[b] if j==len(pos)-1 else None
                idx=point(q,n)
                if ids and idx==ids[-1]:continue
                length=float(np.linalg.norm(q-np.array(xy[ids[-1]]))) if ids else 0
                if ids and length<1e-6:continue
                dist.append((dist[-1] if dist else 0)+length);ids.append(idx)
        if len(ids)>=2:
            ways.append({"way":e["id"],"name":e["tags"].get("name"),"width_m":road_width(e["tags"]),"ids":ids,"s":dist})
    return np.array(xy),ways,node_index,shared,excluded

def solve(reference,ways):
    """Minimax deviation with bounded change of adjacent grades per metre.
    Variables at a junction are literally the same variable, not a post-hoc average.
    """
    n=len(reference)
    rows=[];cols=[];values=[];rhs=[]
    def constraint(items,b):
        k=len(rhs);rhs.append(b)
        for i,v in items:rows.append(k);cols.append(i);values.append(v)
    for i,y in enumerate(reference):
        constraint([(i,1),(n,-1)],float(y))
        constraint([(i,-1),(n,-1)],-float(y))
    for way in ways:
        ids,s=way["ids"],way["s"]
        for j in range(1,len(ids)-1):
            a,b,c=ids[j-1:j+2];d1=s[j]-s[j-1];d2=s[j+1]-s[j]
            terms=[(a,1/d1),(b,-1/d1-1/d2),(c,1/d2)]
            limit=CURVATURE*(d1+d2)/2
            constraint(terms,limit);constraint([(i,-v) for i,v in terms],limit)
    A=coo_matrix((values,(rows,cols)),shape=(len(rhs),n+1)).tocsr()
    obj=np.zeros(n+1);obj[-1]=1
    fit=linprog(obj,A_ub=A,b_ub=rhs,bounds=[(None,None)]*n+[(0,None)],method="highs")
    if not fit.success:raise ValueError("Road profile solver: "+fit.message)
    # Second stage: choose smallest total residual within minimax optimum.
    from scipy.sparse import hstack,vstack,eye
    from scipy.sparse import csr_matrix
    I=eye(n,format="csr")
    Z=csr_matrix((n,1))
    A2=vstack([hstack([A,csr_matrix((A.shape[0],n))]),
               hstack([I,Z,-I]),hstack([-I,Z,-I])],format="csr")
    obj2=np.r_[np.zeros(n+1),np.ones(n)]
    fit2=linprog(obj2,A_ub=A2,b_ub=np.r_[rhs,reference,-reference],
                 bounds=[(None,None)]*n+[(0,float(fit.x[-1])+1e-7)]+[(0,None)]*n,method="highs")
    if not fit2.success:raise ValueError("Road profile residual solver: "+fit2.message)
    return fit2.x[:n]

def metrics(reference,y,ways):
    result=[]
    for w in ways:
        ids=np.array(w["ids"]);s=np.array(w["s"]);h=y[ids]
        grades=np.diff(h)/np.diff(s)
        delta=np.abs(np.diff(grades))
        curvature=delta/((np.diff(s)[:-1]+np.diff(s)[1:])/2)
        result.append({"way":w["way"],"name":w["name"],"samples":len(ids),
                       "max_deviation_m":float(np.max(np.abs(h-reference[ids]))),
                       "max_grade_change":float(delta.max(initial=0)),
                       "max_grade_change_per_3m":float(curvature.max(initial=0)*3)})
    return result
