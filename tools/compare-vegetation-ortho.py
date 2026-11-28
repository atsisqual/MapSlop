#!/usr/bin/env python3
"""Private 2025 orthophoto comparison. Visual review, not tree-level ground truth."""
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds
from PIL import Image,ImageDraw
from terrain_grid import extent,ORIGIN,KX,KY

spec=importlib.util.spec_from_file_location("buildings",Path(__file__).with_name("build-dgt-buildings.py"))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
root,out=map(Path,sys.argv[1:3])
names=["ORTOS-2025-cog-25cm-084-2_v01.tif","ORTOS-2025-cog-25cm-084-4_v01.tif"]
sources=b.verify(root,names,b.TAG)
trees=json.loads((out/"vegetation-candidates.json").read_text())["trees"]
x0,z0,x1,z1=extent()
def crop(name,area,px):
    a,c,d,e=area
    w,h=round((d-a)/px),round((e-c)/px)
    transform=from_bounds(ORIGIN[1]+a/KX,ORIGIN[0]-e/KY,ORIGIN[1]+d/KX,ORIGIN[0]-c/KY,w,h)
    rgb=np.zeros((3,h,w),dtype=np.uint8); coverage=np.zeros((h,w),dtype=bool)
    for source in names:
        with rasterio.open(root/source) as ds:
            if ds.count<3 or ds.crs is None: raise ValueError("Unexpected orthophoto format")
            bands=np.zeros_like(rgb)
            for i in range(3):
                reproject(rasterio.band(ds,i+1),bands[i],dst_transform=transform,dst_crs="EPSG:4326",resampling=Resampling.bilinear)
            mask=np.zeros((h,w),dtype=np.uint8)
            # Extent of a north-up tile, without loading the source raster mask.
            rows,cols=np.indices((h,w))
            from rasterio.warp import transform as tx
            xs=(transform.c+(cols+.5)*transform.a).ravel()
            ys=(transform.f+(rows+.5)*transform.e).ravel()
            xx,yy=tx("EPSG:4326",ds.crs,xs.tolist(),ys.tolist())
            xx=np.asarray(xx).reshape(h,w);yy=np.asarray(yy).reshape(h,w)
            valid=(xx>=ds.bounds.left)&(xx<ds.bounds.right)&(yy>=ds.bounds.bottom)&(yy<ds.bounds.top)
            rgb[:,valid]=bands[:,valid];coverage|=valid
    image=Image.fromarray(np.moveaxis(rgb,0,2),"RGB")
    image.save(out/(name+"-ortho.png"))
    overlay=image.copy();draw=ImageDraw.Draw(overlay);count=0;covered=0
    for t in trees:
        if not (a<=t["x"]<d and c<=t["z"]<e):continue
        x=(t["x"]-a)/(d-a)*w;y=(t["z"]-c)/(e-c)*h;r=t["crown_radius_proxy_m"]/px
        covered+=int(coverage[min(h-1,int(y)),min(w-1,int(x))]);count+=1
        draw.ellipse((x-r,y-r,x+r,y+r),outline="#00ffff",width=1)
        draw.ellipse((x-1.5,y-1.5,x+1.5,y+1.5),fill="#ffdc45")
    overlay.save(out/(name+"-overlay.png"))
    return {"name":name,"world_extent":area,"pixel_m":px,"tile_extent_coverage":float(coverage.mean()),"candidate_count":count,"candidates_in_tile_extent":covered}
# Same-year overview plus deterministic densest forest and settlement windows.
areas=[("pilot",(x0,z0,x1,z1),1.)]
for name,pred in [("forest",lambda t:t["cos_code"].startswith("5.")),("settlement",lambda t:t["cos_code"].startswith("1."))]:
    bins={}
    for t in trees:
        if pred(t):
            key=(int((t["x"]-x0)//120),int((t["z"]-z0)//120));bins[key]=bins.get(key,0)+1
    if bins:
        i,j=max(bins,key=lambda k:(bins[k],-k[0],-k[1]));a=x0+i*120;c=z0+j*120
        areas.append((name,(a,c,min(a+120,x1),min(c+120,z1)),.25))
report={"sources":sources,"year":2025,"comparison":"cyan proxy crown, yellow candidate point; no species or detection accuracy claim; manual review required","crops":[crop(*a) for a in areas]}
(out/"ortho-comparison.json").write_text(json.dumps(report,indent=2)+"\n")
print("ORTHO_COMPARISON",json.dumps(report))
