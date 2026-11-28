"""Offline non-resampling texture atlas for verified same-license RGB/RGBA tiles.
Outputs glTF UV remaps (top-left texture origin); repeat/wrapped UVs are rejected.
"""
import argparse,hashlib,importlib.util,json,math
from pathlib import Path
import numpy as np
from PIL import Image
spec=importlib.util.spec_from_file_location("assets",Path(__file__).with_name("asset-pipeline.py"))
assets=importlib.util.module_from_spec(spec);spec.loader.exec_module(assets)

def atlas(images,gutter=4,max_size=8192):
    if not 1<=gutter<=32 or not images:raise ValueError("Invalid atlas")
    # Deterministic shelf layout. Preserve native pixels and duplicate edges into gutters.
    ims={name:np.asarray(im.convert("RGBA")) for name,im in images.items()}
    order=sorted(ims,key=lambda k:(-ims[k].shape[0],-ims[k].shape[1],k))
    target=max(max(ims[k].shape[1]+2*gutter for k in order),math.ceil(math.sqrt(sum((v.shape[0]+2*gutter)*(v.shape[1]+2*gutter) for v in ims.values()))))
    width=1<<math.ceil(math.log2(target))
    if width>max_size:raise ValueError("Atlas width exceeds limit")
    x=y=row=0;rects={}
    for name in order:
        h,w=ims[name].shape[:2];ww=w+2*gutter;hh=h+2*gutter
        if x+ww>width:x=0;y+=row;row=0
        rects[name]=(x+gutter,y+gutter,w,h)
        x+=ww;row=max(row,hh)
    height=1<<math.ceil(math.log2(y+row))
    if height>max_size:raise ValueError("Atlas height exceeds limit")
    out=np.zeros((height,width,4),np.uint8);remaps={}
    for name,(x,y,w,h) in rects.items():
        padded=np.pad(ims[name],((gutter,gutter),(gutter,gutter),(0,0)),mode="edge")
        out[y-gutter:y+h+gutter,x-gutter:x+w+gutter]=padded
        if not np.array_equal(out[y:y+h,x:x+w],ims[name]):raise ValueError("Texture pixels changed")
        remaps[name]={"rect_px":[x,y,w,h],"offset":[x/width,y/height],"scale":[w/width,h/height]}
    return Image.fromarray(out),remaps

def transform_uv(uv,remap):
    v=np.asarray(uv,float)
    if v.shape[-1]!=2 or not np.isfinite(v).all() or (v<0).any() or (v>1).any():raise ValueError("Wrapped UV unsupported")
    return v*np.asarray(remap["scale"])+np.asarray(remap["offset"])

def main():
    p=argparse.ArgumentParser();p.add_argument("input",type=Path);p.add_argument("manifest",type=Path);p.add_argument("output",type=Path);a=p.parse_args()
    m=assets.provenance(a.input,a.manifest)
    images={name:Image.open(a.input/name) for name in m["files"] if Path(name).suffix.lower() in (".png",".jpg",".jpeg",".webp")}
    im,remaps=atlas(images);a.output.mkdir(parents=True,exist_ok=False);dest=a.output/"atlas.png";im.save(dest)
    report={"pass":True,"size":list(im.size),"source_manifest":m,"remaps":remaps,"sha256":assets.sha(dest),"uv_convention":"glTF top-left, uv_new=uv*scale+offset; only clamp UVs"}
    (a.output/"atlas-report.json").write_text(json.dumps(report,indent=2)+"\n")
if __name__=="__main__":main()
