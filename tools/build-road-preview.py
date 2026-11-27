#!/usr/bin/env python3
import argparse
from contextlib import ExitStack
import importlib.util
import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.merge import merge
from terrain_binary import decode,save
from road_profiles import network,solve,metrics,CURVATURE,MAX_DEVIATION
from road_carve import Corridor,deform,check_surface

spec=importlib.util.spec_from_file_location("dgt_terrain",Path(__file__).with_name("build-dgt-terrain.py"))
dt=importlib.util.module_from_spec(spec);spec.loader.exec_module(dt)

def write(p,r):
    p.write_text(json.dumps(r,indent=2,allow_nan=False)+"\n")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--terrain",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    if dt.digest(a.terrain)!="de37795151e47e5892b4ed8c701968f0bfe60f64f35d9142fc7b89c71ac633d0":
        raise ValueError("Expected reviewed natural TIN")
    original=decode(a.terrain.read_bytes())
    osm=json.loads((dt.ROOT/"data/pedome/pedome-osm.json").read_text())
    x0,z0=original["x0"],original["z0"]
    x1=x0+(original["nx"]-1)*original["cell"]
    z1=z0+(original["nz"]-1)*original["cell"]
    xy,ways,nodes,shared,excluded=network(osm,(x0,z0,x1,z1))
    with ExitStack() as stack:
        ds=[]
        for asset in dt.expected_assets():
            f=a.input/asset["name"];dt.verify_asset(f,asset)
            src=stack.enter_context(rasterio.open(f));dt.check_tile(src);ds.append(src)
        crs=ds[0].crs
        if any(s.crs!=crs for s in ds):raise ValueError("MDT CRS mismatch")
        mosaic,affine=merge(ds,nodata=-9999.,dtype="float32",masked=True)
        dt.check_coverage(mosaic[0],affine,crs)
        reference=dt.sample(mosaic[0],affine,crs,xy[:,0],xy[:,1])-original["base"]
        y=solve(reference,ways)
        # Independent 0.5 m centreline probes, including between optimisation nodes.
        dense=[];pred=[]
        for w in ways:
            for i,j in zip(w["ids"],w["ids"][1:]):
                u=np.linspace(0,1,max(2,int(np.ceil(np.linalg.norm(xy[j]-xy[i])/0.5))+1))
                dense.extend(xy[i]+u[:,None]*(xy[j]-xy[i]))
                pred.extend(y[i]+u*(y[j]-y[i]))
        dense=np.asarray(dense)
        actual=dt.sample(mosaic[0],affine,crs,dense[:,0],dense[:,1])-original["base"]
        dense_error=float(np.max(np.abs(actual-np.array(pred))))
    m=metrics(reference,y,ways)
    maxdev=max(row["max_deviation_m"] for row in m)
    maxgrade=max(row["max_grade_change_per_3m"] for row in m)
    report={"schema":1,"ways":len(ways),"samples":len(xy),"shared_nodes":len(shared),
            "junction_identity_max_m":0.0,"excluded_structures":excluded,"max_deviation_m":maxdev,
            "max_grade_change_per_3m":maxgrade,"dense_samples":len(dense),"dense_max_deviation_m":dense_error,"profile_pass":maxdev<=MAX_DEVIATION+1e-7 and dense_error<=MAX_DEVIATION+1e-7 and maxgrade<=3*CURVATURE+1e-7,
            "way_metrics":m}
    write(a.output/"road-profiles.json",{"schema":1,"xy":xy.tolist(),"height_m":y.tolist(),"mdt_m":reference.tolist(),
        "ways":ways,"junction_nodes":{str(n):nodes[n] for n in shared if n in nodes},"excluded_structures":excluded})
    write(a.output/"road-validation.json",report)
    print(json.dumps({k:v for k,v in report.items() if k!="way_metrics"}),flush=True)
    # Keep candidate evidence even when the profile criteria fail; never approve it.
    corr=Corridor(xy,y,ways,[nodes[n] for n in sorted(shared) if n in nodes])
    try:
        t,carve=deform(original,corr)
        t,storage=save(a.output/"terrain-road-preview.bin",t,compact=True)
        surface=check_surface(t,original,corr)
        report.update(carve=carve,storage=storage,surface=surface,
            surface_pass=surface["transverse_samples"]>0 and surface["max_crossfall_degrees"]<=1
            and surface["max_centre_mesh_profile_delta_m"]<=0.1 and surface["outside_max_change_m"]<=0.1)
    except Exception as exc:
        report.update(surface_pass=False,carve_failure=f"{type(exc).__name__}: {exc}")
    report["pass"]=bool(report["profile_pass"] and report["surface_pass"])
    write(a.output/"road-validation.json",report)
    print(json.dumps({k:v for k,v in report.items() if k!="way_metrics"}),flush=True)
    # Browser workflow evaluates the candidate even if an offline gate failed.
    return 0

if __name__=="__main__":raise SystemExit(main())
