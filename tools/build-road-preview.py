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
from road_profiles import network,solve,metrics,CURVATURE,MAX_DEVIATION,MAX_MEAN_DEVIATION
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
    p.add_argument("--previous-carve",type=Path)
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
        dense=[];aa=[];bb=[];uu=[];way_ids=[]
        for w in ways:
            for i,j in zip(w["ids"],w["ids"][1:]):
                u=np.linspace(0,1,max(2,int(np.ceil(np.linalg.norm(xy[j]-xy[i])/0.5))+1))
                dense.extend(xy[i]+u[:,None]*(xy[j]-xy[i]))
                aa.extend([i]*len(u));bb.extend([j]*len(u));uu.extend(u);way_ids.extend([w["way"]]*len(u))
        dense=np.asarray(dense);aa=np.array(aa);bb=np.array(bb);uu=np.array(uu);way_ids=np.array(way_ids)
        actual=dt.sample(mosaic[0],affine,crs,dense[:,0],dense[:,1])-original["base"]
        y=solve(reference,ways,{"a":aa,"b":bb,"u":uu,"reference":actual})
        pred=y[aa]*(1-uu)+y[bb]*uu
        err=np.abs(actual-pred)
        dense_error=float(err.max())
    m=metrics(reference,y,ways)
    from terrain_grid import ORIGIN,KX,KY
    def probe(i):
        return {"way":int(way_ids[i]),"x_m":float(dense[i,0]),"z_m":float(dense[i,1]),
                "lat":ORIGIN[0]-float(dense[i,1])/KY,"lon":ORIGIN[1]+float(dense[i,0])/KX,
                "mdt_m":float(actual[i]),"profile_m":float(pred[i]),"deviation_m":float(err[i])}
    exceptions=[probe(i) for i in np.flatnonzero(err>MAX_DEVIATION+1e-7)]
    for row in m:
        ee=err[way_ids==row["way"]]
        row["dense_mean_abs_m"]=float(ee.mean())
        row["dense_max_abs_m"]=float(ee.max())
        row["over_1m_samples"]=int(np.count_nonzero(ee>MAX_DEVIATION+1e-7))
    max_mean=max(row["dense_mean_abs_m"] for row in m)
    maxdev=max(row["max_deviation_m"] for row in m)
    maxgrade=max(row["max_grade_change_per_3m"] for row in m)
    report={"schema":1,"ways":len(ways),"samples":len(xy),"shared_nodes":len(shared),
            "junction_identity_max_m":0.0,"excluded_structures":excluded,"max_deviation_m":maxdev,
            "max_grade_change_per_3m":maxgrade,"dense_samples":len(dense),"dense_max_deviation_m":dense_error,"max_way_mean_abs_m":max_mean,"over_1m_count":len(exceptions),"over_1m_samples":exceptions,"profile_pass":maxdev<=MAX_DEVIATION+1e-7 and dense_error<=MAX_DEVIATION+1e-7 and max_mean<=MAX_MEAN_DEVIATION+1e-7 and maxgrade<=3*CURVATURE+1e-7,
            "way_metrics":m}
    write(a.output/"road-profiles.json",{"schema":1,"xy":xy.tolist(),"height_m":y.tolist(),"mdt_m":reference.tolist(),
        "ways":ways,"junction_nodes":{str(n):nodes[n] for n in shared if n in nodes},"excluded_structures":excluded})
    write(a.output/"road-validation.json",report)
    print(json.dumps({k:v for k,v in report.items() if k not in ("way_metrics","over_1m_samples")}),flush=True)
    # Keep candidate evidence even when the profile criteria fail; never approve it.
    corr=Corridor(xy,y,ways,[nodes[n] for n in sorted(shared) if n in nodes])
    if a.previous_carve and a.previous_carve.exists():
        if dt.digest(a.previous_carve)!="adb2429526dda22c7186a1c1655930970a9eabbc93524a5e969fca79a3e85e73":
            raise ValueError("Previous carve hash mismatch")
        previous=check_surface(decode(a.previous_carve.read_bytes()),original,corr,legacy=True)
        report["previous_run_46067363364_crossfall"]={k:v for k,v in previous.items() if "crossfall" in k or k=="transverse_samples"}
        write(a.output/"road-validation.json",report)
        print(json.dumps({"previous_run_46067363364_crossfall":report["previous_run_46067363364_crossfall"]}),flush=True)
    try:
        t,carve=deform(original,corr)
        t,storage=save(a.output/"terrain-road-preview.bin",t,compact=True)
        surface=check_surface(t,original,corr)
        from terrain_tin import TinSampler
        sampler=TinSampler(t)
        mesh_err=np.abs(np.array([sampler(*p) for p in dense])-actual)
        surface["dense_mesh_max_mdt_deviation_m"]=float(mesh_err.max())
        surface["dense_mesh_max_way_mean_mdt_deviation_m"]=max(float(mesh_err[way_ids==way].mean()) for way in set(way_ids))
        surface["dense_mesh_over_1m_count"]=int(np.count_nonzero(mesh_err>MAX_DEVIATION+1e-7))
        surface["dense_mesh_over_1m_samples"]=[{**probe(i),"mesh_deviation_m":float(mesh_err[i])} for i in np.flatnonzero(mesh_err>MAX_DEVIATION+1e-7)]
        report.update(carve=carve,storage=storage,surface=surface,
            surface_pass=surface["transverse_samples"]>0 and surface["max_crossfall_degrees"]<=1
            and surface["max_centre_mesh_profile_delta_m"]<=0.1 and surface["max_junction_mesh_delta_m"]<=0.02 and surface["outside_max_change_m"]<=0.1
            and surface["junction_platform_crossfall_samples"]>0 and surface["max_junction_platform_crossfall_degrees"]<=1
            and surface["near_berm_outside_max_change_m"]<=0.1
            and storage["gzip_bytes"]<1000000 and carve["missing_mandatory_edges"]==0)
    except Exception as exc:
        report.update(surface_pass=False,carve_failure=f"{type(exc).__name__}: {exc}")
    report["pass"]=bool(report["profile_pass"] and report["surface_pass"])
    write(a.output/"road-validation.json",report)
    print(json.dumps({k:v for k,v in report.items() if k!="way_metrics"}),flush=True)
    # Browser workflow evaluates the candidate even if an offline gate failed.
    return 0

if __name__=="__main__":raise SystemExit(main())
