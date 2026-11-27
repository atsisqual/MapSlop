#!/usr/bin/env python3
"""Private offline DGT building-height measurement and Roofer sample preparation."""
import argparse
from contextlib import ExitStack
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import geometry_mask, bounds as geometry_bounds
from rasterio.merge import merge
from rasterio.windows import from_bounds, Window, transform as window_transform
from rasterio.warp import transform_geom
from scipy.ndimage import distance_transform_edt

ROOT=Path(__file__).resolve().parents[1]
TILES=("178494","178495","179494","179495")
TAG="geodata-dgt-pedome-20261127"

def digest(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()

def inventory(tag):
    d=json.loads((ROOT/"docs/research/release-assets-20261127.json").read_text())
    return {a["name"]:a for release in d["releases"] if release["tag"]==tag for a in release["assets"]}

def verify(root,names,tag):
    entries=inventory(tag)
    result=[]
    for name in names:
        p=root/name
        a=entries[name]
        if p.stat().st_size!=a["bytes"] or digest(p)!=a["sha256"]:
            raise ValueError("Input hash or size mismatch: "+name)
        result.append({k:a[k] for k in ("name","bytes","sha256")})
    return result

def read_pair(root):
    with ExitStack() as stack:
        groups=[]
        for kind in ("MDT","MDS"):
            datasets=[stack.enter_context(rasterio.open(root/f"{kind}-50cm-{tile}-07-2025_v02.tif")) for tile in TILES]
            for ds in datasets:
                if ds.crs!=rasterio.crs.CRS.from_epsg(3763) or ds.count!=1 or not (
                    abs(ds.transform.a-0.5)<1e-8 and abs(ds.transform.e+0.5)<1e-8
                    and abs(ds.transform.b)<1e-8 and abs(ds.transform.d)<1e-8):
                    raise ValueError("Expected aligned EPSG:3763 north-up 0.5 m rasters")
            groups.append(datasets)
        for a,b in zip(*groups):
            if a.transform!=b.transform or a.shape!=b.shape:
                raise ValueError("MDT/MDS tile mismatch")
        t0=groups[0][0].transform
        for ds in groups[0]:
            if any(abs(v-round(v))>1e-7 for v in ((ds.transform.c-t0.c)/0.5,(ds.transform.f-t0.f)/0.5)):
                raise ValueError("Tile grid misalignment")
        arrays=[merge(group,nodata=-9999.0,dtype="float32",masked=True) for group in groups]
        (ground,affine),(surface,saffine)=arrays
        if affine!=saffine or ground.shape!=surface.shape:
            raise ValueError("MDT/MDS mosaic alignment mismatch")
        return ground[0],surface[0],affine

def stats(ground,surface,inside):
    """Use pixel centres at least 0.5 m from footprint edges when possible.
    Do not silently convert nodata, negative differences or mixed roofs to valid heights.
    """
    interior=inside & (distance_transform_edt(np.pad(inside,1))[1:-1,1:-1]>1)
    use=interior if np.count_nonzero(interior)>=12 else inside
    count=int(use.sum())
    valid=use & ~np.ma.getmaskarray(ground) & ~np.ma.getmaskarray(surface)
    g=np.asarray(ground.data,dtype=float)
    s=np.asarray(surface.data,dtype=float)
    valid &= np.isfinite(g)&np.isfinite(s)&(g!=-9999)&(s!=-9999)
    good=int(valid.sum())
    d=s[valid]-g[valid]
    plausible=(d>=0.5)&(d<=80)
    n=int(plausible.sum())
    r={"footprint_pixels":int(inside.sum()),"sample_pixels":count,"valid_pixels":good,
       "plausible_pixels":n,"interior_used":use is interior,
       "coverage":good/count if count else 0.0,"plausible_fraction":n/good if good else 0.0,
       "height_m":None,"quality":"fallback","reason":None}
    if count<12 or r["coverage"]<0.8 or good<12:
        r["reason"]="insufficient_coverage"
        return r
    if r["plausible_fraction"]<0.8 or n<12:
        r["reason"]="nonbuilding_or_invalid_difference"
        return r
    q=np.percentile(d[plausible],[10,25,50,75,90,95])
    r.update(p10_m=float(q[0]),p25_m=float(q[1]),p50_m=float(q[2]),p75_m=float(q[3]),
             p90_m=float(q[4]),p95_m=float(q[5]),ground_m=float(np.median(g[valid])),
             roof_absolute_p90_m=float(np.percentile(s[valid][plausible],90)))
    if q[4]-q[0]>max(3.0,0.6*q[2]):
        r["reason"]="heterogeneous_surface_needs_lidar"
        return r
    r.update(height_m=round(float(q[4]),2),quality="raster_candidate",reason=None)
    return r

def measure(ground,surface,affine,geometry):
    projected=transform_geom("EPSG:4326","EPSG:3763",geometry)
    left,bottom,right,top=geometry_bounds(projected)
    win=from_bounds(left,bottom,right,top,affine)
    c0,r0=math.floor(win.col_off),math.floor(win.row_off)
    c1,r1=math.ceil(win.col_off+win.width),math.ceil(win.row_off+win.height)
    if c0<0 or r0<0 or c1>ground.shape[1] or r1>ground.shape[0] or c1<=c0 or r1<=r0:
        return {"height_m":None,"quality":"fallback","reason":"outside_mosaic"}
    local=window_transform(Window(c0,r0,c1-c0,r1-r0),affine)
    inside=geometry_mask([projected],out_shape=(r1-r0,c1-c0),transform=local,invert=True)
    return stats(ground[r0:r1,c0:c1],surface[r0:r1,c0:c1],inside)

def geometry_of(e):
    ring=[(p["lon"],p["lat"]) for p in e.get("geometry",[])]
    if len(ring)<4 or ring[0]!=ring[-1] or len(set(ring[:-1]))<3:
        return None
    return {"type":"Polygon","coordinates":[ring]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--osm",type=Path,default=ROOT/"data/pedome/pedome-osm.json")
    a=ap.parse_args()
    if a.output.exists():ap.error("Output already exists")
    names=[f"{kind}-50cm-{tile}-07-2025_v02.tif" for kind in ("MDT","MDS") for tile in TILES]
    inputs=verify(a.input,names,TAG)
    ground,surface,affine=read_pair(a.input)
    osm=json.loads(a.osm.read_text())
    rows=[];features={}
    for e in osm["elements"]:
        if e["type"]!="way" or "building" not in e.get("tags",{}):continue
        geom=geometry_of(e)
        row={"osm_type":"way","osm_id":e["id"],"osm_height":e["tags"].get("height"),
             "osm_levels":e["tags"].get("building:levels")}
        row.update(measure(ground,surface,affine,geom) if geom else
                   {"height_m":None,"quality":"fallback","reason":"invalid_footprint"})
        rows.append(row)
        if row["height_m"] is not None:
            features[e["id"]]={"type":"Feature","geometry":geom,"properties":{
                "osm_id":str(e["id"]),"h_ground":row["ground_m"],"h_roof":row["roof_absolute_p90_m"]}}
    candidates=sorted((r for r in rows if r["height_m"] is not None),key=lambda r:(r["height_m"],r["osm_id"]))
    # Deterministic spread of roof heights; this is a sample, not a visual validation.
    ids=np.linspace(0,len(candidates)-1,min(20,len(candidates)),dtype=int) if candidates else []
    sample=[candidates[i] for i in ids]
    summary={"schema":1,"source_release":TAG,"source_attribution":"© Direção-Geral do Território, CC BY 4.0",
             "source_crs":"EPSG:3763","pixel_size_m":0.5,"osm_sha256":digest(a.osm),
             "inputs":inputs,"building_count":len(rows),"raster_candidates":len(candidates),
             "fallback_count":len(rows)-len(candidates),"height_quantiles_m":np.percentile(
                 [r["height_m"] for r in candidates],[0,25,50,75,100]).tolist() if candidates else [],
             "sample_osm_ids":[r["osm_id"] for r in sample],"rows":rows}
    # Preserve explicit OSM heights; for other buildings use measured candidates
    # only in a private preview copy, never modify the canonical OSM source.
    candidate_map={r["osm_id"]:r for r in candidates}
    applied=[]
    for e in osm["elements"]:
        if e["type"]!="way" or e["id"] not in candidate_map or "building" not in e.get("tags",{}):
            continue
        row=candidate_map[e["id"]]
        if e["tags"].get("height"):
            row["preview_policy"]="preserve_explicit_osm_height"
            continue
        e["tags"]["height"]=str(row["height_m"])
        row["preview_policy"]="raster_p90_candidate"
        applied.append(e["id"])
    summary["preview_applied_count"]=len(applied)
    summary["preview_applied_osm_ids"]=applied
    a.output.mkdir(parents=True)
    (a.output/"height-preview-osm.json").write_text(json.dumps(osm,allow_nan=False)+"\n")
    (a.output/"building-heights.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    (a.output/"roofer-sample.geojson").write_text(json.dumps({"type":"FeatureCollection","features":[
        features[r["osm_id"]] for r in sample]},allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in summary.items() if k not in ("rows","inputs")}))
    if len(rows)!=527 or len(sample)<20:
        raise ValueError("Expected 527 pilot ways and at least 20 raster candidates")

if __name__=="__main__":
    main()
