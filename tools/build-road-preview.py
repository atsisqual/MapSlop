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
from road_surface_policy import junction_groups,parallel_policy,platform_radii,RAMP

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
    shared_indices=[nodes[n] for n in sorted(shared) if n in nodes]
    parallel,parallel_eq=parallel_policy(xy,ways)
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
        groups,group_eq=junction_groups(xy,ways,shared_indices,reference)
        equalities=group_eq+parallel_eq
        dense=[];aa=[];bb=[];uu=[];way_ids=[]
        for w in ways:
            for i,j in zip(w["ids"],w["ids"][1:]):
                u=np.linspace(0,1,max(2,int(np.ceil(np.linalg.norm(xy[j]-xy[i])/0.5))+1))
                dense.extend(xy[i]+u[:,None]*(xy[j]-xy[i]))
                aa.extend([i]*len(u));bb.extend([j]*len(u));uu.extend(u);way_ids.extend([w["way"]]*len(u))
        dense=np.asarray(dense);aa=np.array(aa);bb=np.array(bb);uu=np.array(uu);way_ids=np.array(way_ids)
        actual=dt.sample(mosaic[0],affine,crs,dense[:,0],dense[:,1])-original["base"]
        observations={"a":aa,"b":bb,"u":uu,"reference":actual}
        # Quantify independently which constraints cause the displacement.
        constraint_trials={}
        for label,eq in (("unconstrained",[]),("groups_only",group_eq),("parallel_only",parallel_eq)):
            trial=solve(reference,ways,observations,adaptive=True,equalities=eq)
            er=np.abs(actual-(trial[aa]*(1-uu)+trial[bb]*uu))
            constraint_trials[label]={"dense_max_m":float(er.max()),"max_way_mean_m":max(float(er[way_ids==w].mean()) for w in set(way_ids))}
        strict=solve(reference,ways,observations,equalities=equalities)
        strict_err=np.abs(actual-(strict[aa]*(1-uu)+strict[bb]*uu))
        adaptive=bool(strict_err.max()>MAX_DEVIATION+1e-7 or any(strict_err[way_ids==w].mean()>MAX_MEAN_DEVIATION+1e-7 for w in set(way_ids)))
        y=solve(reference,ways,observations,adaptive=True,equalities=equalities) if adaptive else strict
        pred=y[aa]*(1-uu)+y[bb]*uu
        err=np.abs(actual-pred)
        dense_error=float(err.max())
    m=metrics(reference,y,ways,adaptive=adaptive)
    from terrain_grid import ORIGIN,KX,KY
    def probe(i):
        return {"way":int(way_ids[i]),"x_m":float(dense[i,0]),"z_m":float(dense[i,1]),
                "lat":ORIGIN[0]-float(dense[i,1])/KY,"lon":ORIGIN[1]+float(dense[i,0])/KX,
                "mdt_m":float(actual[i]),"profile_m":float(pred[i]),"deviation_m":float(err[i])}
    exceptions=[probe(i) for i in np.flatnonzero(err>MAX_DEVIATION+1e-7)]
    worst=[];seen=set()
    for i in np.argsort(-err):
        row=probe(i);key=(row["way"],round(row["x_m"],2),round(row["z_m"],2))
        if key in seen:continue
        seen.add(key)
        row["name"]=next(w.get("name") for w in ways if w["way"]==row["way"])
        if shared_indices:
            j=int(np.argmin(np.linalg.norm(xy[shared_indices]-dense[i],axis=1)))
            row["junction_distance_m"]=float(np.linalg.norm(xy[shared_indices[j]]-dense[i]))
            row["platform_group"]=next(k for k,g in enumerate(groups) if j in g)
        worst.append(row)
        if len(worst)==10:break
    radii=platform_radii(xy,ways,shared_indices,groups)
    group_report=[{"group":k,"node_indices":[shared_indices[j] for j in g],
                   "osm_nodes":[next((n for n,i in nodes.items() if i==shared_indices[j]),None) for j in g],
                   "diameter_m":max((float(np.linalg.norm(xy[shared_indices[i]]-xy[shared_indices[j]])) for i in g for j in g),default=0.),
                   "mdt_span_m":float(np.ptp(reference[[shared_indices[j] for j in g]])),
                   "radius_m":[float(radii[j]) for j in g],"height_m":float(y[shared_indices[g[0]]])} for k,g in enumerate(groups)]
    for row in m:
        ee=err[way_ids==row["way"]]
        row["dense_mean_abs_m"]=float(ee.mean())
        row["dense_max_abs_m"]=float(ee.max())
        row["over_1m_samples"]=int(np.count_nonzero(ee>MAX_DEVIATION+1e-7))
    max_mean=max(row["dense_mean_abs_m"] for row in m)
    maxdev=max(row["max_deviation_m"] for row in m)
    maxgrade=max(row["max_grade_change_per_3m"] for row in m)
    report={"schema":1,"ways":len(ways),"samples":len(xy),"shared_nodes":len(shared),
            "junction_identity_max_m":max((abs(sum(y[i]*v for i,v in terms)) for terms in equalities),default=0.0),"platform_groups":len(groups),"ramp_length_m":RAMP,"parallel_ways":parallel["ways"] if parallel else [],"excluded_structures":[e for e in excluded if e["reason"]!=["low_priority_access_no_carve"]],"excluded_accesses":[e for e in excluded if e["reason"]==["low_priority_access_no_carve"]],"strict_dense_max_deviation_m":float(strict_err.max()),"adaptive_enabled":adaptive,"adaptive_station_count":sum(len(w["adaptive_stations"]) for w in m),"max_deviation_m":maxdev,
            "max_grade_change_per_3m":maxgrade,"dense_samples":len(dense),"dense_max_deviation_m":dense_error,"max_way_mean_abs_m":max_mean,"over_1m_count":len(exceptions),"over_1m_samples":exceptions,"profile_pass":maxdev<=MAX_DEVIATION+1e-7 and dense_error<=MAX_DEVIATION+1e-7 and max_mean<=MAX_MEAN_DEVIATION+1e-7 and all(row["grade_limit_pass"] for row in m),
            "way_metrics":m,"constraint_trials":constraint_trials,"platform_group_details":group_report,"worst_10_mdt_deviation":worst}
    write(a.output/"road-profiles.json",{"schema":1,"xy":xy.tolist(),"height_m":y.tolist(),"mdt_m":reference.tolist(),
        "ways":ways,"platform_group_details":group_report,"junction_nodes":{str(n):nodes[n] for n in shared if n in nodes},"excluded_structures":excluded})
    write(a.output/"road-validation.json",report)
    print(json.dumps({k:v for k,v in report.items() if k not in ("way_metrics","over_1m_samples","platform_group_details")}),flush=True)
    # Keep candidate evidence even when the profile criteria fail; never approve it.
    corr=Corridor(xy,y,ways,shared_indices,groups=groups,parallel=parallel)
    try:
        if a.previous_carve and a.previous_carve.exists():
            if dt.digest(a.previous_carve)!="adb2429526dda22c7186a1c1655930970a9eabbc93524a5e969fca79a3e85e73":
                raise ValueError("Previous carve hash mismatch")
            old_xy,old_ways,old_nodes,old_shared,_=network(osm,(x0,z0,x1,z1),legacy=True)
            old_corr=Corridor(old_xy,np.zeros(len(old_xy)),old_ways,[old_nodes[n] for n in sorted(old_shared) if n in old_nodes])
            previous=check_surface(decode(a.previous_carve.read_bytes()),original,old_corr,legacy=True)
            report["previous_run_46067363364_crossfall"]={k:v for k,v in previous.items() if "crossfall" in k or k=="transverse_samples"}
            write(a.output/"road-validation.json",report)
            print(json.dumps({"previous_run_46067363364_crossfall":report["previous_run_46067363364_crossfall"]}),flush=True)
    except Exception as exc:
        report['optional_historical_diagnostics_error']=f'{type(exc).__name__}: {exc}'
        print(report['optional_historical_diagnostics_error'],flush=True)
    ramp_sections=[{"way":w["way"],"start_xz":xy[w["ids"][0]].tolist(),
                    "ramps":[{"start_m":a,"end_m":b,"length_m":b-a} for a,b in p.ramps],
                    "cores":[{"start_m":a,"end_m":b,"height_m":h} for a,b,h in p.cores]}
                    for w,p in zip(ways,corr.profiles)]
    report["ramp_sections"]=ramp_sections
    p=a.output/"road-profiles.json"
    profiles=json.loads(p.read_text());profiles["ramp_sections"]=ramp_sections;write(p,profiles)
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
            and surface["max_centre_mesh_profile_delta_away_from_ramps_m"] is not None and surface["max_centre_mesh_profile_delta_away_from_ramps_m"]<=0.1 and surface["max_centre_mesh_target_delta_m"]<=0.1
            and surface["ramp_transverse_samples"]>0 and surface["max_ramp_crossfall_degrees"]<=1 and surface["max_junction_mesh_delta_m"]<=0.02 and surface["outside_max_change_m"]<=0.1
            and surface["junction_platform_crossfall_samples"]>0 and surface["max_junction_platform_crossfall_degrees"]<=1
            and surface["near_berm_outside_max_change_m"]<=0.1
            and surface["dense_mesh_max_mdt_deviation_m"]<=1.0 and surface["dense_mesh_max_way_mean_mdt_deviation_m"]<=0.5
            and storage["gzip_bytes"]<1000000 and carve["missing_mandatory_edges"]==0)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        report.update(surface_pass=False,carve_failure=f"{type(exc).__name__}: {exc}")
    report["pass"]=bool(report["profile_pass"] and report["surface_pass"])
    write(a.output/"road-validation.json",report)
    print(json.dumps({k:v for k,v in report.items() if k not in ("way_metrics","ramp_sections")}),flush=True)
    # Browser workflow evaluates the candidate even if an offline gate failed.
    return 0

if __name__=="__main__":raise SystemExit(main())
