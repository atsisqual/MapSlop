"""Deterministic junction and parallel-road constraints. All heights are local metres."""
import numpy as np
RAMP=6.0
PARALLEL_IDS=(657862470,1473693894)

def junction_groups(xy,ways,shared):
    ids=list(shared);radii=np.array([max(w["width_m"]/2 for w in ways if i in w["ids"]) for i in ids])
    parent=list(range(len(ids)))
    def root(i):
        while parent[i]!=i:i=parent[i]
        return i
    for i,a in enumerate(ids):
        for j in range(i):
            if np.linalg.norm(xy[a]-xy[ids[j]])<=radii[i]+radii[j]+.02:parent[root(i)]=root(j)
    groups={}
    for i in range(len(ids)):groups.setdefault(root(i),[]).append(i)
    eq=[]
    for group in groups.values():
        anchor=ids[group[0]]
        for j in group[1:]:eq.append([(ids[j],1),(anchor,-1)])
        # Shared nodes and stations actually within the same flat core must agree.
        for j in group:
            for k in np.flatnonzero(np.linalg.norm(xy-xy[ids[j]],axis=1)<=radii[j]-.02):
                if k!=anchor:eq.append([(int(k),1),(anchor,-1)])
    return list(groups.values()),eq

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
