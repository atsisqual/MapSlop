#!/usr/bin/env python3
"""Estimate flat-roof elevations from paired DGT MDS/MDT and exact game footprints."""
import argparse
from collections import Counter
from contextlib import ExitStack
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import geometry_mask
from rasterio.merge import merge
from rasterio.warp import transform
from rasterio.windows import from_bounds
from affine import Affine
from shapely.geometry import Polygon, mapping
from shapely.ops import transform as transform_geometry
from terrain_binary import decode
from terrain_grid import ORIGIN,KX,KY,validate
from terrain_tin import TinSampler
from building_heights import key,digest

ROOT=Path(__file__).resolve().parents[1]
RELEASE="geodata-dgt-pedome-20261127"
TILES=("178494","178495","179494","179495")
TIN_SHA="93495e59862affea17c7202a089fe3203afb536184ab47740727194da669bb59"
def asset_list():
    inv=json.loads((ROOT/"docs/research/release-assets-20261127.json").read_text())
    assets=next(r["assets"] for r in inv["releases"] if r["tag"]==RELEASE)
    by_name={a["name"]:a for a in assets}
    return [by_name[f"{kind}-50cm-{tile}-07-2025_v02.tif"] for kind in ("MDT","MDS") for tile in TILES]

def open_pair(directory,stack):
    groups={"MDT":[],"MDS":[]}
    metadata=[]
    for a in asset_list():
        p=directory/a["name"]
        if p.stat().st_size!=a["bytes"] or digest(p)!=a["sha256"]:
            raise ValueError("Invalid source hash/size: "+p.name)
        ds=stack.enter_context(rasterio.open(p))
        t=ds.transform
        if ds.count!=1 or not ds.crs or ds.crs.to_epsg()!=3763 or abs(t.a-0.5)>1e-8 or abs(t.e+0.5)>1e-8 or abs(t.b)>1e-8 or abs(t.d)>1e-8:
            raise ValueError("Unexpected raster CRS/resolution: "+p.name)
        groups[p.name[:3]].append(ds)
        metadata.append({**a,"crs":ds.crs.to_string(),"transform":list(t)[:6],"shape":[ds.height,ds.width],"nodata":ds.nodata if ds.nodata is None or math.isfinite(ds.nodata) else str(ds.nodata)})
    for dt,ds in zip(groups["MDT"],groups["MDS"]):
        if dt.crs!=ds.crs or dt.transform!=ds.transform or dt.shape!=ds.shape:
            raise ValueError("Unaligned MDS/MDT tile pair")
    ref=groups["MDT"][0].transform
    for ds in groups["MDT"]:
        if any(abs(v-round(v))>1e-6 for v in ((ds.transform.c-ref.c)/0.5,(ds.transform.f-ref.f)/0.5)):
            raise ValueError("Unaligned tiles")
    dt,a=merge(groups["MDT"],nodata=-9999,dtype="float32",masked=True)
    ds,b=merge(groups["MDS"],nodata=-9999,dtype="float32",masked=True)
    if a!=b or dt.shape!=ds.shape:
        raise ValueError("Unaligned mosaics")
    return dt[0],ds[0],a,metadata

def ring(flat):
    return list(zip(flat[::2],flat[1::2]))

def projected(poly,crs):
    def fn(x,z,y=None):
        lon=ORIGIN[1]+np.asarray(x)/KX
        lat=ORIGIN[0]-np.asarray(z)/KY
        return transform("EPSG:4326",crs,lon.tolist(),lat.tolist())
    return transform_geometry(fn,poly)

def extract(poly,dt,ds,affine):
    """Paired valid samples at pixel centres inside a 0.5 m inset.
    No fill, no smoothing, no replacing missing values with zero.
    """
    inner=poly.buffer(-0.5)
    if inner.is_empty:
        return None,"inset_empty"
    win=from_bounds(*inner.bounds,transform=affine)
    c0,r0=math.floor(win.col_off),math.floor(win.row_off)
    c1,r1=math.ceil(win.col_off+win.width),math.ceil(win.row_off+win.height)
    if c0<0 or r0<0 or c1>dt.shape[1] or r1>dt.shape[0]:
        return None,"outside_raster"
    if c1<=c0 or r1<=r0:
        return None,"no_pixels"
    a=dt[r0:r1,c0:c1]
    b=ds[r0:r1,c0:c1]
    inside=geometry_mask([mapping(inner)],out_shape=a.shape,transform=affine*Affine.translation(c0,r0),invert=True,all_touched=False)
    valid=inside & ~np.ma.getmaskarray(a) & ~np.ma.getmaskarray(b) & np.isfinite(a.data) & np.isfinite(b.data)
    n=int(inside.sum()); nv=int(valid.sum())
    stats={"pixels":n,"valid_pixels":nv,"valid_fraction":nv/n if n else 0.0,"inset_m":0.5}
    if not nv:
        return stats,"no_valid_pixels"
    ground=a.data[valid].astype(np.float64)
    surface=b.data[valid].astype(np.float64)
    delta=surface-ground
    p10,p50,p75,p90=np.percentile(delta,[10,50,75,90])
    stats.update(delta_p10_m=float(p10),delta_p50_m=float(p50),delta_p75_m=float(p75),delta_p90_m=float(p90),
        positive_fraction=float(np.mean(delta>=1.0)),ground_p50_m=float(np.median(ground)),surface_p75_m=float(np.percentile(surface,75)))
    if nv<8 or stats["valid_fraction"]<0.8:return stats,"insufficient_paired_samples"
    if stats["positive_fraction"]<0.8 or not 1.5<=p75<=60:return stats,"implausible_height"
    if p90-p10>max(3.0,0.8*p75):return stats,"high_dispersion"
    return stats,None

def estimate(b,dt,ds,affine,crs,terrain,sampler):
    row={"footprint_key":key(b),"osm_type":b["osmType"],"osm_id":b["id"],"method":"fallback",
         "original_height_m":b["h"],"original_estimated":bool(b.get("est")),"render_height_m":b["h"]}
    poly=Polygon(ring(b["ring"]),[ring(h) for h in b.get("holes",[])])
    if not poly.is_valid or poly.is_empty:
        row["reason"]="invalid_footprint";return row
    row["area_m2"]=float(poly.area)
    x0,z0,x1,z1=poly.bounds
    row["centroid_local_m"]=[float(poly.centroid.x),float(poly.centroid.y)]
    if x0<terrain["x0"] or z0<terrain["z0"] or x1>terrain["x0"]+(terrain["nx"]-1)*terrain["cell"] or z1>terrain["z0"]+(terrain["nz"]-1)*terrain["cell"]:
        row["reason"]="outside_terrain";return row
    if b.get("part") or b.get("podium") or b.get("minH"):
        row["reason"]="building_part_or_elevated";return row
    stats,reason=extract(projected(poly,crs),dt,ds,affine)
    row["samples"]=stats
    if reason:
        row["reason"]=reason;return row
    # MDS p75 sets an absolute flat roof. On a slope use the exact engine footing
    # (minimum at outer ring vertices), not the median ground as the render base.
    footing=min(sampler(x,z) for x,z in ring(b["ring"]))
    roof=stats["surface_p75_m"]-terrain["base"]
    h=roof-footing
    if not 1.5<=h<=80:
        row["reason"]="implausible_render_height";return row
    # Explicit OSM height/levels are retained when a strong disagreement requires review.
    if not b.get("est") and abs(h-b["h"])>max(3.0,b["h"]*0.35):
        row["reason"]="conflicts_with_osm_height";return row
    row.update(method="mds_mdt",reason="accepted_heuristic",render_height_m=round(h,3),
        roof_relative_m=round(roof,3),footing_relative_m=float(footing),nominal_height_m=stats["delta_p75_m"])
    return row

def summary(rows):
    used=[r for r in rows if r["method"]=="mds_mdt"]
    heights=[r["render_height_m"] for r in used]
    # deterministic audit sample: range-spanning 20 from accepted, plus fallback reason examples
    ordered=sorted(used,key=lambda r:(r["render_height_m"],r["footprint_key"]))
    picks=[ordered[i] for i in np.linspace(0,len(ordered)-1,min(20,len(ordered)),dtype=int)] if ordered else []
    fallback={}
    for r in rows:
        if r["method"]=="fallback":fallback.setdefault(r["reason"],r)
    return {"buildings":len(rows),"measured":len(used),"fallback":len(rows)-len(used),
        "reasons":dict(Counter(r["reason"] for r in rows)),
        "height_distribution_m":dict(zip(("min","p10","median","p90","max"),map(float,np.percentile(heights,[0,10,50,90,100])))) if heights else None,
        "audit_sample_20":[r["footprint_key"] for r in picks],
        "fallback_examples":[r["footprint_key"] for r in fallback.values()]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--footprints",type=Path,required=True)
    p.add_argument("--terrain",type=Path,required=True)
    p.add_argument("--osm",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():p.error("Output already exists")
    if digest(a.terrain)!=TIN_SHA:raise ValueError("Approved terrain SHA mismatch")
    terrain=validate(decode(a.terrain.read_bytes()))
    sampler=TinSampler(terrain)
    fp=json.loads(a.footprints.read_text())
    if fp["osm_sha256"]!=digest(a.osm):raise ValueError("Footprint provenance mismatch")
    with ExitStack() as stack:
        dt,ds,affine,metadata=open_pair(a.input,stack)
        rows=[estimate(b,dt,ds,affine,"EPSG:3763",terrain,sampler) for b in fp["buildings"]]
    s=summary(rows)
    report={"schema":1,"source":"DGT MDS-MDT 0.5 m","source_release":RELEASE,"source_crs":"EPSG:3763",
        "license_status":"DGT MDT terms unresolved; private derivatives only; OSM ODbL 1.0",
        "inputs":metadata,"terrain_sha256":digest(a.terrain),"osm_sha256":digest(a.osm),
        "footprints_sha256":digest(a.footprints),"script_sha256":digest(Path(__file__)),
        "method":"paired pixel centres, 0.5 m inset, delta p75 and absolute MDS p75, engine footing",
        "rasterio_version":rasterio.__version__,"numpy_version":np.__version__,"summary":s,"buildings":rows}
    a.output.write_text(json.dumps(report,ensure_ascii=False,allow_nan=False,separators=(",",":"))+"\n")
    print(json.dumps({"report_sha256":digest(a.output),"bytes":a.output.stat().st_size,
        **{k:v for k,v in s.items() if k not in ("audit_sample_20","fallback_examples")}}))
    if s["measured"]<20:raise SystemExit("Insufficient accepted buildings for 20-sample review")
if __name__=="__main__":
    main()
