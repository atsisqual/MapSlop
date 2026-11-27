#!/usr/bin/env python3
"""Generate local-grid terrain from the four immutable DGT MDT pilot tiles.

This is an offline conversion, not a downloader. Do not publish the products until
the rights for the DGT MDT collection have been reconciled.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.warp import transform, transform_bounds
from rasterio.windows import from_bounds

from terrain_grid import BBOX, ORIGIN, KX, KY, extent, grid_shape, height_at, validate, to_world
from terrain_tin import build_tin, TinSampler
from terrain_binary import save as save_binary

RELEASE = "geodata-dgt-pedome-20261127"
TILES = ("178494","178495","179494","179495")
ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "docs/research/release-assets-20261127.json"

def digest(p):
    with p.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()

def expected_assets(inventory=INVENTORY):
    data=json.loads(inventory.read_text(encoding="utf-8"))
    assets=next(r["assets"] for r in data["releases"] if r["tag"]==RELEASE)
    names=[f"MDT-50cm-{tile}-07-2025_v02.tif" for tile in TILES]
    return [next(a for a in assets if a["name"]==name) for name in names]

def verify_asset(path, asset):
    if path.stat().st_size!=asset["bytes"] or digest(path)!=asset["sha256"]:
        raise ValueError("Source size/SHA-256 mismatch: "+path.name)

def check_tile(ds):
    t=ds.transform
    if ds.count!=1 or not ds.crs or not ds.crs.is_projected or ds.crs.linear_units.lower() not in {"metre","meter","metres","meters","m"}:
        raise ValueError("Expected single-band projected metric MDT")
    if abs(t.a-0.5)>1e-8 or abs(t.e+0.5)>1e-8 or abs(t.b)>1e-8 or abs(t.d)>1e-8:
        raise ValueError("Expected north-up 0.5 m MDT")
    a=ds.read(1,masked=True)
    return {"crs":ds.crs.to_string(),"crs_wkt":ds.crs.to_wkt(),
            "width":ds.width,"height":ds.height,"transform":list(t)[:6],
            "nodata":ds.nodata if ds.nodata is None or math.isfinite(ds.nodata) else str(ds.nodata),
            "invalid_pixels":int(np.count_nonzero(np.ma.getmaskarray(a)|~np.isfinite(a.data))),
            "unit":ds.units[0],"vertical_datum": "not independently verified"}

def sample(mosaic, affine, crs, x, z):
    """Bilinear sample pixel centres in source CRS at exact engine-frame points."""
    xx=np.asarray(x,dtype=np.float64)
    zz=np.asarray(z,dtype=np.float64)
    lon=ORIGIN[1]+xx.ravel()/KX
    lat=ORIGIN[0]-zz.ravel()/KY
    sx,sy=transform("EPSG:4326",crs,lon.tolist(),lat.tolist())
    col,row=(~affine)*(np.asarray(sx),np.asarray(sy))
    col,row=col-0.5,row-0.5
    i,j=np.floor(col).astype(np.int64),np.floor(row).astype(np.int64)
    if np.any(i<0)|np.any(j<0)|np.any(i+1>=mosaic.shape[1])|np.any(j+1>=mosaic.shape[0]):
        raise ValueError("Terrain sample outside source coverage")
    u,v=col-i,row-j
    a,b,c,d=mosaic[j,i],mosaic[j,i+1],mosaic[j+1,i],mosaic[j+1,i+1]
    valid=~(np.ma.getmaskarray(a)|np.ma.getmaskarray(b)|np.ma.getmaskarray(c)|np.ma.getmaskarray(d))
    values=(a*(1-u)*(1-v)+b*u*(1-v)+c*(1-u)*v+d*u*v)
    if not np.all(valid) or not np.all(np.isfinite(values.data)):
        raise ValueError("NoData/nonfinite in terrain samples")
    return np.asarray(values).reshape(xx.shape)

def check_coverage(mosaic, affine, crs):
    s,w,n,e=BBOX
    b=transform_bounds("EPSG:4326",crs,w,s,e,n,densify_pts=21)
    win=from_bounds(*b,transform=affine)
    c0,r0=math.floor(win.col_off),math.floor(win.row_off)
    c1,r1=math.ceil(win.col_off+win.width),math.ceil(win.row_off+win.height)
    if c0<0 or r0<0 or c1>mosaic.shape[1] or r1>mosaic.shape[0]:
        raise ValueError("Pilot envelope outside mosaic")
    a=mosaic[r0:r1,c0:c1]
    invalid=int(np.count_nonzero(np.ma.getmaskarray(a)|~np.isfinite(a.data)))
    if invalid:
        raise ValueError(f"Pilot source envelope contains {invalid} invalid pixels")
    return {"projected_envelope":list(b),"pixels_checked":int(a.size),"invalid_pixels":invalid}

def build_grid(mosaic, affine, crs, cell, bounds=None, source="DGT MDT 0.5 m"):
    x0,z0,nx,nz=grid_shape(cell,bounds)
    x,z=np.meshgrid(x0+np.arange(nx)*cell,z0+np.arange(nz)*cell)
    base=float(sample(mosaic,affine,crs,np.array([0.0]),np.array([0.0]))[0])
    values=sample(mosaic,affine,crs,x,z)-base
    t=dict(source=source,origin_lat_lon=list(ORIGIN),base=round(base,3),
           x0=x0,z0=z0,cell=cell,nx=nx,nz=nz,
           heights=np.round(values,3).ravel().tolist())
    return validate(t,bounds)

def compare(t,mosaic,affine,crs,bounds=None,sampler=None):
    """100 deterministic off-grid interior points; compare to source bilinear height."""
    x0,z0,x1,z1=extent() if bounds is None else bounds
    x,z=np.meshgrid(x0+(np.arange(10)+0.37)*(x1-x0)/10,
                    z0+(np.arange(10)+0.63)*(z1-z0)/10)
    ref=sample(mosaic,affine,crs,x,z).ravel()
    query=sampler or (lambda x,z: height_at(t,x,z))
    actual=np.array([t["base"]+query(float(a),float(b)) for a,b in zip(x.ravel(),z.ravel())])
    err=np.abs(actual-ref)
    return {"points":int(err.size),"max_abs_m":float(err.max()),"mean_abs_m":float(err.mean()),"rmse_m":float(np.sqrt(np.mean(err**2))),
            "within_1m":int(np.count_nonzero(err<=1.0)),
            "point_errors":[{"x":round(float(a),3),"z":round(float(b),3),"abs_error_m":round(float(c),5)}
                            for a,b,c in zip(x.ravel(),z.ravel(),err)]}

def road_samples(osm):
    """Sample surface drivable centrelines every <=0.5 m, including two
    lateral traces at +/-1.5 m (representative wheel corridors, not surveyed kerbs).
    Restrict to pilot; exclude bridges/tunnels/layers rather than comparing their decks to ground.
    """
    kinds={"motorway","trunk","primary","secondary","tertiary","unclassified","residential","living_street","service"}
    x0,z0,x1,z1=extent()
    points=[]
    details=[]
    ways=0
    for e in osm["elements"]:
        t=e.get("tags",{})
        if e.get("type")!="way" or t.get("highway","").removesuffix("_link") not in kinds:
            continue
        if t.get("bridge","no")!="no" or t.get("tunnel","no")!="no" or t.get("layer","0")!="0" or t.get("area")=="yes":
            continue
        geom=[to_world(p["lon"],p["lat"]) for p in e.get("geometry",[])]
        start=len(points)
        for (ax,az),(bx,bz) in zip(geom,geom[1:]):
            dx,dz=bx-ax,bz-az
            length=math.hypot(dx,dz)
            if length<1e-6:
                continue
            if max(ax,bx)<x0-2 or min(ax,bx)>x1+2 or max(az,bz)<z0-2 or min(az,bz)>z1+2:
                continue
            for u in np.linspace(0,1,max(2,math.ceil(length/0.5)+1)):
                for offset in (-1.5,0.0,1.5):
                    x=ax+dx*u-dz/length*offset
                    z=az+dz*u+dx/length*offset
                    if x0<=x<=x1 and z0<=z<=z1:
                        points.append((x,z))
                        details.append({"way":e["id"],"name":t.get("name"),"highway":t.get("highway"),"offset_m":offset})
        if len(points)>start:
            ways+=1
    if not points:
        raise ValueError("No eligible surface road samples")
    return np.array(points),ways,details

def compare_roads(t,points,ways,reference,details,sampler=None):
    query=sampler or (lambda x,z: height_at(t,x,z))
    values=np.array([t["base"]+query(float(x),float(z)) for x,z in points])
    errors=np.abs(values-reference)
    # Stable tie order; report original OSM identity and both coordinate frames.
    worst=np.argsort(-errors,kind="stable")[:10]
    top=[{**details[i],"x_m":float(points[i,0]),"z_m":float(points[i,1]),
          "lon":float(ORIGIN[1]+points[i,0]/KX),"lat":float(ORIGIN[0]-points[i,1]/KY),
          "reference_m":float(reference[i]),"mesh_m":float(values[i]),"error_m":float(errors[i]),
          "signed_error_m":float(values[i]-reference[i])} for i in worst]
    return {"points":len(points),"ways":ways,"step_m":0.5,"offsets_m":[-1.5,0,1.5],"worst_10":top,
            "max_abs_m":float(errors.max()),"mean_abs_m":float(errors.mean()),
            "rmse_m":float(np.sqrt(np.mean(errors**2)))}

def write_json(p,data):
    p.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":"),allow_nan=False)+"\n",encoding="utf-8")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--primary-cell",type=int,choices=(1,2,5),default=2)
    args=p.parse_args()
    if args.output.exists():
        p.error("Output must not already exist")
    assets=expected_assets()
    with ExitStack() as stack:
        sources=[]
        metadata=[]
        for a in assets:
            f=args.input/a["name"]
            verify_asset(f,a)
            ds=stack.enter_context(rasterio.open(f))
            md=check_tile(ds)
            metadata.append({**a,**md})
            sources.append(ds)
        crs=sources[0].crs
        t0=sources[0].transform
        for ds in sources[1:]:
            if ds.crs!=crs or any(abs(v-round(v))>1e-6 for v in ((ds.transform.c-t0.c)/0.5,(ds.transform.f-t0.f)/0.5)):
                raise ValueError("Tiles have inconsistent CRS or pixel alignment")
        arr,affine=merge(sources,nodata=-9999.0,dtype="float32",masked=True)
        mosaic=arr[0]
        coverage=check_coverage(mosaic,affine,crs)
        args.output.mkdir(parents=True)
        points,ways,details=road_samples(json.loads((ROOT/'data/pedome/pedome-osm.json').read_text()))
        reference=sample(mosaic,affine,crs,points[:,0],points[:,1])
        products=[]
        for cell in sorted({args.primary_cell,2,5,10}):
            t=build_grid(mosaic,affine,crs,cell)
            file=args.output/f"terrain-{cell}m.bin"
            t,storage=save_binary(file,t)
            validate(t)
            error=compare(t,mosaic,affine,crs)
            products.append({"kind":"grid",**storage,
                "cell_m":cell,"nx":t["nx"],"nz":t["nz"],"vertices":t["nx"]*t["nz"],
                "triangles":2*(t["nx"]-1)*(t["nz"]-1),"error":error,"roads":compare_roads(t,points,ways,reference,details)})
        tin_failure=None
        try:
            t=build_tin(mosaic,affine,crs,sample,road_points=points,road_reference=reference,road_centres=points[np.array([d['offset_m']==0 for d in details])])
            f=args.output/"terrain-tin.bin"
            t,storage=save_binary(f,t)
            validate(t)
            sampler=TinSampler(t)
            products.append({"kind":"tin",**storage,
                "vertices":len(t["vertices"])//3,"triangles":len(t["triangles"])//3,
                "algorithm":t["algorithm"],"target_error_m":t["target_error_m"],"library_error_m":t["library_error_m"],"refinement":t.get("refinement"),"raster_max_abs_m":t.get("raster_max_abs_m"),
                "error":compare(t,mosaic,affine,crs,sampler=sampler),"roads":compare_roads(t,points,ways,reference,details,sampler)})
        except Exception as exc:
            tin_failure=f'{type(exc).__name__}: {exc}'
            print('TIN candidate failed:',tin_failure,file=sys.stderr)
        primary=next(x for x in products if x.get("cell_m")==args.primary_cell)
        report={"schema":2,"source_release":RELEASE,"source_attribution":"Direção-Geral do Território (DGT)",
                "license_status":"MDT STAC proprietary conflicts with institutional open-data policy; do not publish",
                "bbox_s_w_n_e":list(BBOX),"origin_lat_lon":list(ORIGIN),"frame":"x east, z south, y up, metres",
                "source_crs":crs.to_string(),"source_crs_wkt":crs.to_wkt(),"source_resolution_m":0.5,
                "coverage":coverage,"inputs":metadata,"products":products,"tin_failure":tin_failure,
                "grid_candidate_cell_m":args.primary_cell,"grid_candidate_precision_pass":primary["error"]["max_abs_m"]<=0.5 and primary["roads"]["max_abs_m"]<=0.5,
                "validation_status":"pending","final_pass":None,"default":None,
                "command":"python tools/build-dgt-terrain.py --input "+str(args.input)+" --output "+str(args.output)+" --primary-cell "+str(args.primary_cell),
                "script_sha256":digest(Path(__file__)),
                "frame_sha256":digest(Path(__file__).with_name("terrain_grid.py")),
                "tin_script_sha256":digest(Path(__file__).with_name("terrain_tin.py")),
                "binary_script_sha256":digest(Path(__file__).with_name("terrain_binary.py")),
                "rasterio":rasterio.__version__,"numpy":np.__version__}
        write_json(args.output/"manifest.json",report)
        print(json.dumps({"source_count":len(metadata),"source_crs":crs.to_string(),"coverage_pixels":coverage["pixels_checked"],
            "invalid_pixels":coverage["invalid_pixels"],"products":[{k:v for k,v in x.items() if k!="error"} |
            {"points":x["error"]["points"],"max_abs_m":x["error"]["max_abs_m"],"mean_abs_m":x["error"]["mean_abs_m"],"rmse_m":x["error"]["rmse_m"]} for x in products],
            "grid_candidate_precision_pass":report["grid_candidate_precision_pass"],"validation_status":"pending","final_pass":None}))
        return 0  # aggregate validation decides acceptance; generation alone is not a pass

if __name__=="__main__":
    sys.exit(main())
