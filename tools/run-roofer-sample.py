#!/usr/bin/env python3
"""Run the archived standalone Roofer tool on a private sample, record failures."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import os
import stat
import tarfile
import tempfile
import laspy

spec=importlib.util.spec_from_file_location("buildings",Path(__file__).with_name("build-dgt-buildings.py"))
b=importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

def summarize(output,ids):
    by_id={}
    for p in sorted(output.rglob("*.jsonl")):
        for line in p.read_text().splitlines():
            if not line.strip():continue
            obj=json.loads(line)
            if obj.get("type")!="CityJSONFeature":continue
            key=str(obj.get("id"))
            if key not in ids:continue
            objects=obj.get("CityObjects",{})
            lod22=[g for o in objects.values() for g in o.get("geometry",[]) if str(g.get("lod"))=="2.2" and g.get("boundaries")]
            attrs=objects.get(key,{}).get("attributes",{})
            by_id[key]={"lod22_geometries":len(lod22),"roofer_success":attrs.get("rf_success"),
                        "roof_type":attrs.get("rf_roof_type"),"rmse_lod22":attrs.get("rf_rmse_lod22"),
                        "point_density":attrs.get("rf_pt_density"),"val3dity_lod22":attrs.get("rf_val3dity_lod22")}
    rows=[{"osm_id":key,**by_id.get(key,{"lod22_geometries":0,"reason":"missing_feature"})} for key in sorted(ids)]
    for row in rows:
        row["geometry_policy"]="roofer_lod22_candidate" if row["lod22_geometries"]>0 else "procedural_fallback"
        if row["geometry_policy"]=="procedural_fallback":row["fallback_reason"]=row.get("roof_type") or row.get("reason") or "no_lod22_geometry"
    return {"requested":len(ids),"features_found":len(by_id),
            "with_lod22_geometry":sum(r["lod22_geometries"]>0 for r in rows),"rows":rows}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,required=True)
    ap.add_argument("--measurements",type=Path,required=True)
    ap.add_argument("--toolchain",type=Path,required=True)
    a=ap.parse_args()
    archive="roofer-linux-x86_64-v1.0.0.tar.gz"
    assets=b.verify(a.toolchain,[archive],"reconstruction-toolchain-20261127")
    names=[f"LO-{tile}-07-2025_v05.laz" for tile in b.TILES]
    inputs=b.verify(a.input,names,b.TAG)
    headers=[]
    for name in names:
        with laspy.open(a.input/name) as reader:
            h=reader.header
            crs=h.parse_crs()
            horizontal=next((c for c in crs.sub_crs_list if c.is_projected),crs) if crs is not None else None
            if horizontal is None or horizontal.to_epsg()!=3763:
                raise ValueError("LAZ horizontal CRS not confirmed EPSG:3763: "+name)
            headers.append({"name":name,"point_count":int(h.point_count),"crs":crs.to_string(),
                            "version":str(h.version),"point_format":h.point_format.id})
    root=a.measurements
    sample=json.loads((root/"roofer-sample.geojson").read_text())
    ids={str(f["properties"]["osm_id"]) for f in sample["features"]}
    if len(ids)!=20:raise ValueError("Expected twenty unique footprints")
    subprocess.run(["ogr2ogr","-f","GPKG","-s_srs","EPSG:4326","-t_srs","EPSG:3763",
                    str(root/"roofer-sample.gpkg"),str(root/"roofer-sample.geojson")],check=True)
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        with tarfile.open(a.toolchain/archive) as tar:
            tar.extractall(td,filter="data")
        candidates=[p for p in td.rglob("roofer") if p.is_file()]
        if len(candidates)!=1:raise ValueError("Unexpected Roofer archive layout")
        exe=candidates[0]
        # The archive may have been transferred without executable mode.
        exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        for lib in td.rglob("*.so*"):
            if lib.is_file() and not lib.is_symlink():
                lib.chmod(lib.stat().st_mode | stat.S_IRUSR | stat.S_IXUSR)
        env=os.environ.copy()
        libdirs=sorted({str(p.parent) for p in td.rglob("*.so*") if p.is_file()})
        if libdirs:
            env["LD_LIBRARY_PATH"]=os.pathsep.join(libdirs+([env["LD_LIBRARY_PATH"]] if env.get("LD_LIBRARY_PATH") else []))
        version=subprocess.check_output([str(exe),"--version"],text=True,stderr=subprocess.STDOUT,env=env).strip()
        print("ROOFER_VERSION",version,flush=True)
        output=root/"roofer-output"
        output.mkdir()
        command=[str(exe),"--id-attribute","osm_id","--h-terrain-attribute","h_ground","--lod22",
                 "--bld-class","6","--grnd-class","2",str(a.input/"cloud"),str(root/"roofer-sample.gpkg"),str(output)]
        # One folder is one pointcloud source/acquisition, not four competing surveys.
        cloud=a.input/"cloud"
        cloud.mkdir()
        for name in names:(cloud/name).symlink_to((a.input/name).resolve())
        with (root/"roofer.log").open("w") as log:
            rc=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=1800,env=env).returncode
        report={"roofer_version":version,"exit_code":rc,"inputs":inputs,"toolchain":assets,
                "headers":headers,**summarize(output,ids)}
        (root/"roofer-summary.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
        print(json.dumps(report,allow_nan=False))
        with tarfile.open(root/"roofer-cityjson.tar.gz","w:gz") as tar:
            for p in sorted(output.rglob("*.jsonl")):
                tar.add(p,arcname=str(p.relative_to(output)))
        if rc or report["with_lod22_geometry"]==0:raise RuntimeError("Roofer trial failed or produced no LoD2.2")

if __name__=="__main__":
    main()
