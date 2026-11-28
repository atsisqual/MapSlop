#!/usr/bin/env python3
"""Private DGT 2025 orthophoto tile pyramid in the exact MapSlop local frame."""
import argparse
import hashlib
import gzip
import importlib.util
import json
import math
from pathlib import Path
from contextlib import ExitStack
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.transform import from_bounds
from PIL import Image
from terrain_grid import ORIGIN, KX, KY
from terrain_binary import decode

spec=importlib.util.spec_from_file_location("buildings",Path(__file__).with_name("build-dgt-buildings.py"))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
NAMES=["ORTOS-2025-cog-25cm-084-2_v01.tif","ORTOS-2025-cog-25cm-084-4_v01.tif"]
TILE=128
GUTTER=2
LEVELS=[("far",64,75),("mid",128,78),("near",512,82)]
def digest(path):
    with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def world_bounds(x0,z0,x1,z1):
    return (ORIGIN[1]+x0/KX,ORIGIN[0]-z1/KY,ORIGIN[1]+x1/KX,ORIGIN[0]-z0/KY)
def render_tile(datasets,x,z):
    size=next(n for l,n,_ in LEVELS if l=="near")
    bounds=world_bounds(x-GUTTER,z-GUTTER,x+TILE+GUTTER,z+TILE+GUTTER)
    affine=from_bounds(*bounds,size,size)
    rgb=np.full((3,size,size),65535,dtype=np.uint16)
    for ds in datasets:
        left,bottom,right,top=transform_bounds("EPSG:4326",ds.crs,*bounds)
        if right<=ds.bounds.left or left>=ds.bounds.right or top<=ds.bounds.bottom or bottom>=ds.bounds.top:continue
        arr=np.full_like(rgb,65535)
        for i in range(3):
            reproject(rasterio.band(ds,i+1),arr[i],dst_transform=affine,dst_crs="EPSG:4326",dst_nodata=65535,resampling=Resampling.bilinear)
        ok=np.all(arr!=65535,axis=0)
        rgb[:,ok]=arr[:,ok]
    covered=np.all(rgb!=65535,axis=0)
    if not covered.all():raise ValueError(f"Orthophoto missing pixels at {x},{z}: {covered.mean():.6f}")
    return Image.fromarray(np.moveaxis(rgb.astype(np.uint8),0,2),"RGB")
def offline_chain(target):
    # Decode the exact encoded base; average in linear light, then encode sRGB.
    # Bottom-up RGBA bytes match THREE.DataTexture flipY=false and terrain UVs.
    rgb=np.asarray(Image.open(target).convert("RGB"),dtype=np.float32)/255
    linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
    chunks=[];sizes=[]
    while True:
        h,w=linear.shape[:2]
        srgb=np.where(linear<=.0031308,linear*12.92,1.055*np.maximum(linear,0)**(1/2.4)-.055)
        rgba=np.empty((h,w,4),dtype=np.uint8)
        rgba[:,:,:3]=np.rint(np.clip(srgb,0,1)*255).astype(np.uint8);rgba[:,:,3]=255
        raw=rgba[::-1].tobytes();chunks.append(raw);sizes.append({"px":w,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()})
        if w==1:break
        linear=linear.reshape(h//2,2,w//2,2,3).mean(axis=(1,3))
    pack=target.with_suffix(".rgba.gz")
    pack.write_bytes(gzip.compress(b"".join(chunks),compresslevel=6,mtime=0))
    return {"path":pack.name,"bytes":pack.stat().st_size,"sha256":digest(pack),"levels":sizes,"format":"rgba8-bottom-up-srgb-gzip-v1"}
def main():
    p=argparse.ArgumentParser();p.add_argument("--input",type=Path,required=True);p.add_argument("--terrain",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    sources=b.verify(a.input,NAMES,b.TAG)
    terrain=decode(a.terrain.read_bytes())
    if digest(a.terrain)!="36019dfc27584d667555c794350107c29981da4f4ee15bac2c03078aba0d895b":raise ValueError("Unapproved terrain")
    x0,z0=terrain["x0"],terrain["z0"]
    x1,z1=x0+(terrain["nx"]-1)*terrain["cell"],z0+(terrain["nz"]-1)*terrain["cell"]
    cols,rows=math.ceil((x1-x0)/TILE),math.ceil((z1-z0)/TILE)
    a.output.mkdir(parents=True,exist_ok=False)
    manifest={"schema":1,"year":2025,"attribution":"© Direção-Geral do Território, ortofotos 2025; CC BY 4.0; reprojected and cropped by MapSlop","license":"https://creativecommons.org/licenses/by/4.0/","origin_lat_lon":list(ORIGIN),"terrain_sha256":digest(a.terrain),"world_extent":[x0,z0,x1,z1],"tile_m":TILE,"gutter_m":GUTTER,"cols":cols,"rows":rows,"sources":sources,"tiles":[]}
    manifest["sampling"]="pot-v1";manifest["source_metres_per_pixel"]=.25;manifest["offline_mips"]="rgba8-bottom-up-srgb-gzip-v1"
    total={l:0 for l,_,_ in LEVELS}
    with ExitStack() as stack:
        ds=[stack.enter_context(rasterio.open(a.input/n)) for n in NAMES]
        for d in ds:
            if d.crs is None or d.crs.to_epsg()!=3763 or d.count<3 or any(t!="uint8" for t in d.dtypes[:3]) or any(abs(v-.25)>1e-6 for v in d.res) or d.transform.b or d.transform.d:raise ValueError("Expected north-up 25 cm RGB EPSG:3763")
        manifest["raster_metadata"]=[{"crs":d.crs.to_string(),"resolution":list(d.res),"bounds":list(d.bounds)} for d in ds]
        for j in range(rows):
            for i in range(cols):
                x,z=x0+i*TILE,z0+j*TILE
                image=render_tile(ds,x,z)
                record={"i":i,"j":j,"bounds":[x,z,x+TILE,z+TILE],"levels":{}}
                for name,n,q in LEVELS:
                    assert n>0 and n&(n-1)==0
                    px=(TILE+2*GUTTER)/n
                    target=a.output/f"{i}-{j}-{name}-pot{n}.webp"
                    (image if n==image.width else image.resize((n,n),Image.Resampling.LANCZOS)).save(target,"WEBP",quality=q,method=4)
                    size=target.stat().st_size
                    if size>262144:raise ValueError("Tile exceeds 256 KiB")
                    total[name]+=size
                    record["levels"][name]={"path":target.name,"px":n,"metres_per_pixel":px,"mip_levels":n.bit_length(),"bytes":size,"sha256":digest(target),"offline":offline_chain(target)}
                manifest["tiles"].append(record)
    if total["far"]>1_000_000:raise ValueError("Far pyramid exceeds initial transfer budget")
    manifest["bytes_by_level"]=total
    (a.output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("ORTHO_TILES",json.dumps({"tiles":len(manifest["tiles"]),"bytes_by_level":total,"terrain_sha256":manifest["terrain_sha256"],"coverage":1.0}))
if __name__=="__main__":main()
