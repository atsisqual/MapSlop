#!/usr/bin/env python3
"""Private, reproducible LAZ vegetation candidates. Not a species inventory."""
import argparse
from collections import Counter
from contextlib import ExitStack
import importlib.util
import json
import math
from pathlib import Path
import laspy
import numpy as np
import rasterio
from rasterio.merge import merge
from pyproj import Transformer
from scipy.ndimage import maximum_filter,distance_transform_edt
import shapely as sh
from shapely.geometry import LineString,Polygon,shape,box
from shapely.ops import transform
from terrain_grid import extent,to_world,ORIGIN

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("buildings",Path(__file__).with_name("build-dgt-buildings.py"))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
CELL=1.0
OSM_SHA="948fa4269ba8eaa9d995711005d2c8a5413ac4ea16f69838ef031e870b032037"
COS_SHA="3e0e5b01691969b837d7274ea78492d51877bcf665ba423e5aea867d41f13dde"
def read_ground(root):
    with ExitStack() as stack:
        ds=[stack.enter_context(rasterio.open(root/f"MDT-50cm-{t}-07-2025_v02.tif")) for t in b.TILES]
        for d in ds:
            if d.crs.to_epsg()!=3763 or d.count!=1 or d.transform.a!=.5 or d.transform.e!=-.5 or d.transform.b or d.transform.d:
                raise ValueError("Unexpected MDT grid")
        a,t=merge(ds,nodata=-9999.,dtype="float32",masked=True)
        return a[0],t

def width(tags):
    try:
        w=float(str(tags.get("width","")).removesuffix(" m"))
        if .5<=w<=40:return w
    except ValueError:pass
    k=tags.get("highway","")
    if k in ("footway","path","steps","cycleway"):return 2.5
    try:n=float(tags.get("lanes",0))
    except ValueError:n=0
    if not 1<=n<=12:
        n=4 if k in ("motorway","trunk","primary") else 1 if k in ("service","track","living_street") or k.endswith("_link") else 2
        if tags.get("oneway") in ("yes","1","-1") and n>1:n/=2
    return 3.3*n+1

def exclusions(osm):
    areas=[]
    for e in osm["elements"]:
        tags=e.get("tags",{});g=e.get("geometry",[])
        if len(g)<2:continue
        pts=[to_world(p["lon"],p["lat"]) for p in g]
        if "highway" in tags and tags["highway"] not in ("footway","path","steps","cycleway","pedestrian","bridleway","corridor","construction","proposed"):
            areas.append(LineString(pts).buffer(width(tags)/2))
        if ("building" in tags or "building:part" in tags) and len(pts)>=4 and pts[0]==pts[-1]:
            areas.append(Polygon(pts).buffer(0))
    return sh.union_all(areas)

def candidates(high,count,x0,z0,blocked,cos):
    # Local peaks of the high-vegetation return envelope, not individual
    # surveyed trees. Radius is a bounded occupancy proxy.
    occupied=(high>=2.5)&(count>=3)
    support=maximum_filter(high,size=5)
    radii=np.clip(distance_transform_edt(occupied),.8,5.)
    iy,ix=np.nonzero(occupied&(high==support))
    order=np.lexsort((ix,iy,-high[iy,ix]))
    polys=[transform(lambda x,y,z=None:to_world(np.asarray(x),np.asarray(y)),shape(f["geometry"])).buffer(0) for f in cos["features"]]
    codes=[str(f["properties"]["cos25v1_n4_c"]) for f in cos["features"]]
    tree=sh.STRtree(polys);out=[];seen=set();rejected=Counter()
    for i in order:
        r,c=int(iy[i]),int(ix[i]);x=x0+c+.5;z=z0+r+.5
        point=sh.Point(x,z);radius=float(radii[r,c])
        if blocked.distance(point)<=.5:
            rejected["road_or_building_trunk_overlap"]+=1;continue
        matches=tree.query(point,predicate="intersects")
        unique={codes[j] for j in matches}
        if len(unique)!=1:
            rejected["missing_or_ambiguous_cos"]+=1;continue
        code=unique.pop()
        if code.startswith(("1.5.","9.")):
            rejected["cos_road_or_water"]+=1;continue
        # Spatial nonmaximum suppression, deterministic and independent of tile order.
        if any((a,bb) in seen for a in range(r-3,r+4) for bb in range(c-3,c+4) if (a-r)**2+(bb-c)**2<=9):
            rejected["nearer_higher_peak"]+=1;continue
        seen.add((r,c))
        out.append({"x":round(x,2),"z":round(z,2),"height_m":round(float(high[r,c]),2),
                    "crown_radius_proxy_m":round(radius,2),"cos_code":code,
                    "class":5,"cell_returns":int(count[r,c]),"source":"DGT_LAZ_class5"})
    return out,dict(rejected),int(occupied.sum())

def main():
    p=argparse.ArgumentParser();p.add_argument("--input",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    names=[f"{kind}-{t}-07-2025_{version}.{ext}" for t in b.TILES for kind,version,ext in (("LO","v05","laz"),("MDT-50cm","v02","tif"))]
    sources=b.verify(a.input,names,b.TAG)
    osm_path=ROOT/"data/pedome/pedome-osm.json";cos_path=ROOT/"data/pedome/cos2025-pilot.geojson"
    if b.digest(osm_path)!=OSM_SHA or b.digest(cos_path)!=COS_SHA:raise ValueError("Unexpected OSM/COS bytes")
    osm=json.loads(osm_path.read_text());cos=json.loads(cos_path.read_text())
    ground,t=read_ground(a.input);g=np.asarray(ground.data);gmask=np.ma.getmaskarray(ground)
    x0,z0,x1,z1=extent();x0,z0=math.floor(x0),math.floor(z0)
    nx,nz=math.ceil(x1-x0),math.ceil(z1-z0);size=nx*nz
    grid=np.zeros((3,size),dtype=np.uint32);high=np.zeros(size,dtype=np.float32)
    coverage=np.zeros(size,dtype=bool);classes=Counter();valid=Counter();headers=[]
    tr=Transformer.from_crs(3763,4326,always_xy=True)
    inverse=Transformer.from_crs(4326,3763,always_xy=True)
    corners=[inverse.transform(ORIGIN[1]+0,ORIGIN[0]+0)] # check transform eagerly
    from terrain_grid import KX,KY
    xy=[inverse.transform(ORIGIN[1]+x/KX,ORIGIN[0]-z/KY) for x in (x0,x1) for z in (z0,z1)]
    xmin,xmax=min(p[0] for p in xy)-2,max(p[0] for p in xy)+2
    ymin,ymax=min(p[1] for p in xy)-2,max(p[1] for p in xy)+2
    for tile in b.TILES:
        name=f"LO-{tile}-07-2025_v05.laz"
        with laspy.open(a.input/name) as reader:
            h=reader.header;crs=h.parse_crs()
            horizontal=next((c for c in crs.sub_crs_list if c.is_projected),crs) if crs is not None else None
            if horizontal is None or horizontal.to_epsg()!=3763:raise ValueError("Unexpected LAZ CRS "+name)
            headers.append({"name":name,"point_count":int(h.point_count),"crs":crs.to_string()})
            for chunk in reader.chunk_iterator(1_000_000):
                ex,ny=np.asarray(chunk.x),np.asarray(chunk.y)
                hit=(ex>=xmin)&(ex<=xmax)&(ny>=ymin)&(ny<=ymax)
                if not hit.any():continue
                ex,ny=ex[hit],ny[hit];alt=np.asarray(chunk.z)[hit];cl=np.asarray(chunk.classification)[hit]
                lon,lat=tr.transform(ex,ny);xx,zz=to_world(lon,lat)
                keep=(xx>=x0)&(xx<x1)&(zz>=z0)&(zz<z1)
                ex,ny,alt,cl,xx,zz=(v[keep] for v in (ex,ny,alt,cl,xx,zz))
                idx=np.floor(zz-z0).astype(int)*nx+np.floor(xx-x0).astype(int)
                coverage[idx]=True
                for k,n in zip(*np.unique(cl,return_counts=True)):classes[int(k)]+=int(n)
                use=(cl>=3)&(cl<=5)
                ex,ny,alt,cl,idx=(v[use] for v in (ex,ny,alt,cl,idx))
                rr=np.floor((ny-t.f)/t.e).astype(int);cc=np.floor((ex-t.c)/t.a).astype(int)
                inside=(rr>=0)&(rr<g.shape[0])&(cc>=0)&(cc<g.shape[1])
                rr,cc,alt,cl,idx=(v[inside] for v in (rr,cc,alt,cl,idx))
                dh=alt-g[rr,cc]
                good=~gmask[rr,cc]&np.isfinite(dh)&(dh>=.15)&(dh<=45)
                for k in (3,4,5):
                    ok=good&(cl==k);valid[k]+=int(ok.sum())
                    np.add.at(grid[k-3],idx[ok],1)
                    if k==5:np.maximum.at(high,idx[ok],dh[ok])
    if not classes[5] or not valid[5]:raise ValueError("No high vegetation returns")
    # 5 m coverage from all classes; edge cells may be partly outside AOI.
    coarse=np.pad(coverage.reshape(nz,nx),((0,(-nz)%5),(0,(-nx)%5))).reshape(math.ceil(nz/5),5,math.ceil(nx/5),5).any(axis=(1,3))
    cov=float(coarse.mean())
    if cov<.95:raise ValueError(f"Insufficient point coverage {cov:.3f}")
    blocked=exclusions(osm)
    trees,rejected,occupied=candidates(high.reshape(nz,nx),grid[2].reshape(nz,nx),x0,z0,blocked,cos)
    if not trees:raise ValueError("No viable tree candidates")
    report={"schema":1,"sources":sources,"headers":headers,"osm_sha256":OSM_SHA,"cos_sha256":COS_SHA,
            "classification_counts":dict(classes),"plausible_height_returns":dict(valid),
            "coverage_5m_fraction":cov,"height_reference":"absolute LAZ z minus nearest valid 0.5m MDT pixel, EPSG:3763",
            "origin_lat_lon":list(ORIGIN),"high_vegetation_cells":occupied,"tree_candidates":len(trees),
            "rejections":rejected,"height_quantiles_m":np.quantile([v["height_m"] for v in trees],[0,.25,.5,.75,1]).tolist(),
            "crown_radius_proxy_quantiles_m":np.quantile([v["crown_radius_proxy_m"] for v in trees],[0,.25,.5,.75,1]).tolist(),
            "by_cos":dict(Counter(v["cos_code"] for v in trees)),
            "low_medium_vegetation_cells":{str(k):int(np.count_nonzero(grid[k-3])) for k in (3,4)},
            "visual_validated":False,"lod_validated":False}
    for name,data in (("vegetation-candidates.json",{"origin_lat_lon":list(ORIGIN),"trees":trees}),("vegetation-report.json",report)):
        (a.output/name).write_text(json.dumps(data,separators=(",",":"),allow_nan=False)+"\n")
    print(json.dumps(report,allow_nan=False),flush=True)
if __name__=="__main__":main()
