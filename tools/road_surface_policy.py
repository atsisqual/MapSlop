"""Deterministic junction and parallel-road constraints. All heights are local metres."""
import numpy as np
RAMP=6.0
PARALLEL_IDS=(657862470,1473693894)

MAX_GROUP_DIAMETER=6.0
MAX_GROUP_NODES=2
MAX_GROUP_MDT_SPAN=.4
MIN_RADIUS=.02

def junction_groups(xy,ways,shared,reference=None):
    """Complete-link pairs only; no chaining or equality to unrelated nearby stations."""
    ids=list(shared)
    radii=np.array([max(w["width_m"]/2 for w in ways if i in w["ids"]) for i in ids])
    incident={i:{w.get("way",j) for j,w in enumerate(ways) if i in w["ids"]} for i in ids}
    groups=[[j] for j in range(len(ids))]
    candidates=[]
    for i in range(len(ids)):
        for j in range(i):
            d=float(np.linalg.norm(xy[ids[i]]-xy[ids[j]]))
            if d<=min(MAX_GROUP_DIAMETER,radii[i]+radii[j]) and incident[ids[i]]&incident[ids[j]]:
                if reference is not None and abs(reference[ids[i]]-reference[ids[j]])>MAX_GROUP_MDT_SPAN:continue
                candidates.append((d,j,i))
    for _,j,i in sorted(candidates):
        a=next(g for g in groups if j in g);b=next(g for g in groups if i in g)
        if a is b or len(a)+len(b)>MAX_GROUP_NODES:continue
        groups.remove(a);groups.remove(b);groups.append(sorted(a+b))
    groups.sort(key=lambda g:g[0])
    eq=[]
    for g in groups:
        for j in g[1:]:eq.append([(ids[j],1),(ids[g[0]],-1)])
    return groups,eq

def platform_radii(xy,ways,shared,groups):
    ids=list(shared)
    r=np.array([max(w["width_m"]/2 for w in ways if i in w["ids"]) for i in ids],dtype=float)
    membership={i:k for k,g in enumerate(groups) for i in g}
    # Independent cores cannot overlap at different elevations. Shrink each
    # to < half the centre spacing; retain the full six-metre ramp outside.
    for i in range(len(ids)):
        for j in range(i):
            if membership[i]==membership[j]:continue
            d=float(np.linalg.norm(xy[ids[i]]-xy[ids[j]]))
            if d<.04:raise ValueError("Distinct junctions within centimetre precision")
            if d<r[i]+r[j]+.02:
                r[i]=min(r[i],max(MIN_RADIUS,.45*d));r[j]=min(r[j],max(MIN_RADIUS,.45*d))
    return r

def parallel_policy(xy,ways):
    a=next((w for w in ways if w.get("way")==PARALLEL_IDS[0]),None)
    b=next((w for w in ways if w.get("way")==PARALLEL_IDS[1]),None)
    if not a or not b:return None,[]
    aa=np.array(a["ids"]);bb=np.array(b["ids"]);axis=xy[aa[-1]]-xy[aa[0]]
    axis/=np.linalg.norm(axis)
    s=xy[aa]@axis
    if np.any(np.diff(s)<=0):raise ValueError("Parallel reference station not monotonic")
    t=xy[bb]@axis
    lo=max(float(s[0]),float(t.min()));hi=min(float(s[-1]),float(t.max()))
    if hi-lo<6:raise ValueError("Parallel overlap too short")
    eq=[]
    for i,v in zip(bb,t):
        if not lo-1e-6<=v<=hi+1e-6:continue
        j=min(len(s)-2,max(0,int(np.searchsorted(s,v)-1)));u=float(np.clip((v-s[j])/(s[j+1]-s[j]),0,1))
        eq.append([(int(i),1),(int(aa[j]),u-1),(int(aa[j+1]),-u)])
    order=np.argsort(t)
    return {"ids":aa,"axis":axis,"stations":s,"lo":lo,"hi":hi,"ways":list(PARALLEL_IDS),
            "other_ids":bb[order],"other_stations":t[order],"half_a":a["width_m"]/2,"half_b":b["width_m"]/2},eq
