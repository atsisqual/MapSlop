"""Station-based C1 road profiles. No radial height override on paved strips."""
import numpy as np
from scipy.interpolate import PchipInterpolator
from road_surface_policy import RAMP

def hermite(s,a,b,y0,y1,m0,m1):
    t=np.clip((np.asarray(s)-a)/(b-a),0,1);u=1-t
    return (1+2*t)*u*u*y0+t*u*u*(b-a)*m0+t*t*(3-2*t)*y1-t*t*u*(b-a)*m1

class SectionProfile:
    def __init__(self,stations,heights,anchors=()):
        self.s=np.asarray(stations,dtype=float);self.y=np.asarray(heights,dtype=float)
        self.base=PchipInterpolator(self.s,self.y)
        self.derivative=self.base.derivative()
        self.intervals=[];self.ramps=[];self.cores=[]
        # A plateau ends where its centreline exits the core, not a second
        # half carriageway beyond the core. Only incident nodes impose ramps.
        for s,r,h in sorted(anchors):
            a,b=max(self.s[0],s-r),min(self.s[-1],s+r)
            if b<a:continue
            if self.cores and a<self.cores[-1][1]+1e-8:
                pa,pb,ph=self.cores[-1]
                if abs(ph-h)>1e-5:raise ValueError("Different platform heights overlap along a road")
                self.cores[-1]=(pa,max(pb,b),ph)
            else:self.cores.append((a,b,h))
        for i,(a,b,h) in enumerate(self.cores):
            lo=self.cores[i-1][1] if i else self.s[0]
            hi=self.cores[i+1][0] if i+1<len(self.cores) else self.s[-1]
            # Extend the transition on steep approaches: endpoint slope is
            # matched, rather than blending the road and a radial disk.
            def length(s):return float(np.clip(RAMP+40*abs(float(self.derivative(s))),RAMP,12.))
            if i==0:
                x=max(lo,a-length(a))
                if a-x>1e-7:self.add(x,a,float(self.base(x)),h,float(self.derivative(x)),0.)
            self.intervals.append((a,b,h,h,0.,0.))
            if i+1<len(self.cores):
                next_a,_,next_h=self.cores[i+1]
                end=min(next_a,b+length(b))
                start=max(b,next_a-length(next_a))
                if end>=start:
                    if next_a-b>1e-7:self.add(b,next_a,h,next_h,0.,0.)
                else:
                    self.add(b,end,h,float(self.base(end)),0.,float(self.derivative(end)))
                    self.add(start,next_a,float(self.base(start)),next_h,float(self.derivative(start)),0.)
            else:
                x=min(hi,b+length(b))
                if x-b>1e-7:self.add(b,x,h,float(self.base(x)),0.,float(self.derivative(x)))
        self.knots=sorted(set(self.s.tolist()+[v for a,b,*_ in self.intervals for v in (a,b)]+
                              [float(x) for a,b in self.ramps for x in np.linspace(a,b,max(2,int(np.ceil((b-a)/.85))+1))]))
    def add(self,a,b,y0,y1,m0,m1):
        if b-a<=1e-7:return
        self.intervals.append((a,b,y0,y1,m0,m1));self.ramps.append((a,b))
    def at(self,s):
        q=np.clip(np.asarray(s,dtype=float),self.s[0],self.s[-1])
        out=np.asarray(self.base(q))
        for a,b,y0,y1,m0,m1 in self.intervals:
            mask=(q>=a-1e-8)&(q<=b+1e-8)
            if b-a<=1e-7:out=np.where(mask,y0,out)
            else:out=np.where(mask,hermite(q,a,b,y0,y1,m0,m1),out)
        return out
    def in_ramp(self,s):
        return any(a-1e-7<=s<=b+1e-7 for a,b in self.ramps)
