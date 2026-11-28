"""Procedural, explicitly estimated facade details for footprint-based models.
Configurable through per-building YAML metadata; no claims of photographic accuracy.
"""
import math
import numpy as np
from shapely.geometry import Point
import shapely as sh

def facade(p,ground,height,config):
    # Input is a local metric polygon; elevations refer to the existing terrain datum.
    ring=np.asarray(p.exterior.coords)[:-1];ccw=bool(sh.is_ccw(p.exterior))
    edges=[]
    for i,(a,b) in enumerate(zip(ring,np.roll(ring,-1,axis=0))):
        d=b-a;length=float(np.linalg.norm(d))
        if length<.15:continue
        u=d/length;normal=np.array([u[1],-u[0]])*(1 if ccw else -1)
        edges.append((i,a,u,normal,length))
    result={"granite":[],"door":[],"window":[]};report={"door":0,"window":0,"quoin_strips":0,"procedural":True}
    entrance=config.get("porta_principal") or {}
    windows=config.get("janelas") or {}
    quoins=config.get("cunhais_granito") or {}
    az=float(entrance.get("azimute_graus",270));direction=np.array([math.sin(math.radians(az)),-math.cos(math.radians(az))])
    if not 0<=az<360:raise ValueError("Door azimuth outside [0,360)")
    possible=[e for e in edges if e[4]>=2.8]
    if not possible:raise ValueError("No suitable facade edge")
    chosen=max(possible,key=lambda e:(float(e[3]@direction),e[4]))
    if entrance.get("aresta") is not None:
        chosen=next(e for e in possible if e[0]==int(entrance["aresta"]))
    def quad(kind,e,t0,t1,y0,y1,offset=.045):
        i,a,u,n,l=e
        if not (0<=t0<t1<=l) or y1<=y0:return False
        def point(t,y):
            q=a+u*t+n*offset
            return (float(q[0]),float(y),float(q[1]))
        A,B,C,D=point(t0,y0),point(t1,y0),point(t1,y1),point(t0,y1)
        result[kind].extend([[A,B,C],[A,C,D]]);return True
    def opening(kind,e,t,width,sill,h,frame):
        i,a,u,n,l=e;left=t-width/2;right=t+width/2
        if left-frame<.15 or right+frame>l-.15:return False
        q=a+u*t;base=ground(float(q[0]),float(q[1]));y0=base+sill;y1=y0+h
        # Check top at both ends, with margin below the roof.
        for k in (left-frame,t,right+frame):
            pt=a+u*k
            if y1+frame>height(*pt)-.18:return False
        if not quad(kind,e,left,right,y0,y1,.052):return False
        quad("granite",e,left-frame,left,y0-frame,y1+frame,.075)
        quad("granite",e,right,right+frame,y0-frame,y1+frame,.075)
        quad("granite",e,left,right,y1,y1+frame,.075)
        if kind=="window":quad("granite",e,left,right,y0-frame,y0,.075)
        report[kind]+=1;return True
    if entrance.get("enabled",True):
        fraction=float(entrance.get("fracao_aresta",.5));w=float(entrance.get("largura_m",1.5));h=float(entrance.get("altura_m",2.55))
        if not .1<=fraction<=.9 or not .5<=w<=3 or not 1<=h<=4:raise ValueError("Invalid door configuration")
        if not opening("door",chosen,chosen[4]*fraction,w,.04,h,.20):
            if entrance.get("aresta") is not None:raise ValueError("Explicit configured door does not fit")
            # Default estimated orientation may be ambiguous; try other edges without
            # changing the explicitly configured width/height.
            for alternative in sorted(possible,key=lambda e:(float(e[3]@direction),e[4]),reverse=True):
                if alternative[0]==chosen[0]:continue
                if opening("door",alternative,alternative[4]*.5,w,.04,h,.20):
                    chosen=alternative;report["door_fallback"]="estimated orientation fallback";break
            else:raise ValueError("No suitable facade for estimated door")
        report["door_edge"]=chosen[0]
    if windows.get("enabled",True):
        w=float(windows.get("largura_m",.75));h=float(windows.get("altura_m",1.4));sill=float(windows.get("peitoril_m",2.1));spacing=float(windows.get("intervalo_m",4.2))
        if not .3<=w<=2 or not .5<=h<=3 or not .3<=sill<=8 or spacing<2:raise ValueError("Invalid window configuration")
        explicit=windows.get("posicoes")
        if explicit is not None:
            for item in explicit:
                e=next(e for e in edges if e[0]==int(item["aresta"]))
                if not opening("window",e,e[4]*float(item["fracao_aresta"]),w,sill,h,.15):raise ValueError("Configured window does not fit")
        else:
            for e in edges:
                if e[0]==chosen[0] or e[4]<3.6:continue
                n=max(1,int(e[4]/spacing))
                for k in range(n):opening("window",e,e[4]*(k+.5)/n,w,sill,h,.15)
    if quoins.get("enabled",True):
        w=float(quoins.get("largura_m",.28))
        if not .12<=w<=.8:raise ValueError("Invalid quoin width")
        # Convex corners: apply narrow strips to the adjacent edge surfaces.
        for e in edges:
            if e[4]<2*w+.2:continue
            for l,r in ((.015,w),(e[4]-w,e[4]-.015)):
                a,u=e[1:3];q=a+u*((l+r)/2)
                base=ground(*q);top=min(height(*(a+u*l)),height(*(a+u*r)))-.06
                if top>base+.5 and quad("granite",e,l,r,base,top,.06):report["quoin_strips"]+=1
    cornice=config.get("cornija_granito") or {}
    report["cornice_segments"]=0
    if cornice.get("enabled",False):
        h=float(cornice.get("altura_m",.22))
        if not .1<=h<=.5:raise ValueError("Invalid cornice height")
        for e in edges:
            i,a,u,n,l=e
            steps=max(1,math.ceil(l/.5))
            for k in range(steps):
                t0,t1=l*k/steps,l*(k+1)/steps
                A=a+u*t0;B=a+u*t1
                y0=height(*A)-.04;y1=height(*B)-.04
                if min(y0-ground(*A),y1-ground(*B))<h+.3:continue
                A=A+n*.09;B=B+n*.09
                points=[(float(A[0]),y0-h,float(A[1])),(float(B[0]),y1-h,float(B[1])),(float(B[0]),y1,float(B[1])),(float(A[0]),y0,float(A[1]))]
                result["granite"].extend([[points[0],points[1],points[2]],[points[0],points[2],points[3]]]);report["cornice_segments"]+=1
    return result,report
