#!/usr/bin/env python3
"""Aggregate acceptance metrics without publishing source grids."""
import argparse
import json
import os
from pathlib import Path

def summarize(manifest,browser_dir):
    rows=[]
    for cell in (2,5):
        p=next(x for x in manifest["products"] if x["cell_m"]==cell)
        f=browser_dir/str(cell)/"browser-report.json"
        b=json.loads(f.read_text()) if f.is_file() else {}
        t=b.get("terrain",{})
        e=p["error"]
        row={"cell_m":cell,"vertices":p["vertices"],"json_bytes":p["bytes"],"sha256":p["sha256"],
             "points":e["points"],"max_abs_m":e["max_abs_m"],"mean_abs_m":e["mean_abs_m"],"rmse_m":e["rmse_m"],
             "distance_m":b.get("distance"),"contact_m":t.get("contact"),"contact_samples":t.get("contactSamples"),
             "contact_max_m":t.get("contactDuringDrive",{}).get("max"),
             "contact_mean_m":t.get("contactDuringDrive",{}).get("mean"),
             "surface_contact_max_m":t.get("collisionSurfaceDuringDrive",{}).get("max"),
             "browser_success":b.get("success",False),"multi_touch":b.get("multiTouch",False),"touch_release":b.get("touchRelease",False)}
        row["pass"]=bool(e["points"]==100 and e["max_abs_m"]<=1 and row["browser_success"]
                         and t.get("cell")==cell and t.get("source")=="DGT MDT 0.5 m"
                         and row["distance_m"] is not None and row["distance_m"]>2
                         and row["contact_samples"] is not None and row["contact_samples"]>=3
                         and row["contact_max_m"] is not None and row["contact_max_m"]<=0.5
                         and row["surface_contact_max_m"] is not None and row["surface_contact_max_m"]<=0.5
                         and row["multi_touch"] and row["touch_release"])
        rows.append(row)
    passed=all(r["pass"] for r in rows) and manifest["coverage"]["invalid_pixels"]==0
    return {"schema":1,"tested_commit":os.getenv("GITHUB_SHA"),"branch":os.getenv("GITHUB_REF_NAME"),
            "run_id":os.getenv("GITHUB_RUN_ID"),"source_release":manifest["source_release"],
            "source_crs":manifest["source_crs"],"coverage_pixels":manifest["coverage"]["pixels_checked"],
            "invalid_pixels":manifest["coverage"]["invalid_pixels"],"inputs":[{k:a[k] for k in ("name","bytes","sha256")} for a in manifest["inputs"]],
            "results":rows,"recommended_default_cell_m":(5 if rows[0]["vertices"]>150000 else 2) if passed else None,
            "pass":passed}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--terrain",type=Path,required=True)
    ap.add_argument("--browser",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    report=summarize(json.loads((a.terrain/"manifest.json").read_text()),a.browser)
    a.output.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,allow_nan=False))
    return 0 if report["pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
