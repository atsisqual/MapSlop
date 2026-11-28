#!/usr/bin/env python3
"""Deterministic multi-view textured 3D scene. Synthetic data, no third-party photos."""
import argparse,hashlib,json
from pathlib import Path
import cv2
import numpy as np
def main():
    p=argparse.ArgumentParser();p.add_argument("output",type=Path);p.add_argument("--aerial",action="store_true");a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    rng=np.random.default_rng(352);size=768;surfaces=[]
    # Three noncoplanar surfaces (backdrop, floor, side wall). Distinct random texture and large-scale geometry.
    quads=[[[-4,-2,3],[4,-2,3],[4,3,3],[-4,3,3]],[[-4,-2,-3],[4,-2,-3],[4,-2,3],[-4,-2,3]],[[-4,-2,-3],[-4,-2,3],[-4,3,3],[-4,3,-3]]]
    if a.aerial:quads=[[[-6,0,-6],[6,0,-6],[6,0,6],[-6,0,6]],[[-2,1,-2],[1,1,-2],[1,1,1],[-2,1,1]],[[2,1.5,1],[4,1.5,1],[4,1.5,3],[2,1.5,3]]]
    for quad in quads:
        tex=rng.integers(50,210,(size,size,3),dtype=np.uint8)
        tex=cv2.GaussianBlur(tex,(5,5),.9)
        for i in range(650):
            x,y=rng.integers(5,size-5,2);color=tuple(map(int,rng.integers(0,255,3)))
            cv2.circle(tex,(int(x),int(y)),int(rng.integers(3,14)),color,-1)
            if i%7==0:cv2.putText(tex,str(i),(int(x),int(y)),cv2.FONT_HERSHEY_SIMPLEX,.45,color,1,cv2.LINE_AA)
        surfaces.append((np.array(quad,float),tex))
    W,H=960,720;f=780.;src=np.array([[0,0],[size-1,0],[size-1,size-1],[0,size-1]],np.float32);files={};geo=["EPSG:32629"]
    for i in range(15):
        eye=np.array([-1.4+2.8*i/14,.3+.2*np.sin(i*.7),-6.5+.15*np.cos(i*.8)])
        target=np.array([-.2,-.25,1.])
        if a.aerial:
            eye=np.array([-2+2*(i%3),7.5,-2+1*(i//3)]);target=eye+np.array([.08,-1,.09])
        forward=target-eye;forward/=np.linalg.norm(forward)
        right=np.cross(forward,[0,1,0]);right/=np.linalg.norm(right);up=np.cross(right,forward)
        canvas=np.full((H,W,3),128,np.uint8)
        for q,t in sorted(surfaces,key=lambda s:-np.linalg.norm(s[0].mean(0)-eye)):
            rel=q-eye;depth=rel@forward
            pix=np.column_stack((W/2+f*(rel@right)/depth,H/2-f*(rel@up)/depth)).astype(np.float32)
            mat=cv2.getPerspectiveTransform(src,pix)
            img=cv2.warpPerspective(t,mat,(W,H));mask=cv2.warpPerspective(np.full(t.shape[:2],255,np.uint8),mat,(W,H))
            canvas[mask>250]=img[mask>250]
        name=f"view-{i:02d}.jpg";path=a.output/name;cv2.imwrite(str(path),canvas,[cv2.IMWRITE_JPEG_QUALITY,95]);files[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        geo.append(f"{name} {500000+eye[0]:.6f} {4600000-eye[2]:.6f} {100+eye[1]:.6f}")
    if a.aerial:
        path=a.output/"geo.txt";path.write_text("\n".join(geo)+"\n");files[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    (a.output/"manifest.json").write_text(json.dumps({"source_type":"synthetic","license":"MIT","author":"MapSlop generator","reviewed_by":"CI fixture","source_url_or_archive":"tools/generate-photo-fixture.py","files":files,"camera_params":[780,780,480,360]},indent=2))
if __name__=="__main__":main()
