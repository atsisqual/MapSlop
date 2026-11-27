#!/usr/bin/env python3
"""Aggregate private validation metrics, pick near terrain without requiring distant LODs to pass."""
import argparse
import hashlib
import shutil
import json
import os
from pathlib import Path

def summarize(manifest,browser_dir):
    rows=[]
    for p in manifest["products"]:
        kind=p.get("kind","grid")
        cell=p.get("cell_m")
        label="tin" if kind=="tin" else str(cell)
        f=browser_dir/label/"browser-report.json"
        b=json.loads(f.read_text()) if f.is_file() else {}
        t=b.get("terrain",{})
        e=p["error"]
        road=p["roads"]
        drive=b.get("longDrive",{})
        row={"kind":kind,"cell_m":cell,"file":p["file"],"vertices":p["vertices"],"triangles":p["triangles"],
             "raw_bytes":p["bytes"],"gzip_bytes":p.get("gzip_bytes"),"encoding":p.get("encoding"),"exact_float32_geometry":p.get("exact_float32_geometry"),"legacy_binary_bytes":p.get("legacy_binary_bytes"),"legacy_binary_gzip_bytes":p.get("legacy_binary_gzip_bytes"),"gzip_sha256":p.get("gzip_sha256"),"json_bytes":p.get("json_bytes"),"json_gzip_bytes":p.get("json_gzip_bytes"),"sha256":p["sha256"],"points":e["points"],
             "max_abs_m":e["max_abs_m"],"mean_abs_m":e["mean_abs_m"],"rmse_m":e["rmse_m"],
             "road_points":road["points"],"road_ways":road["ways"],"road_max_abs_m":road["max_abs_m"],
             "road_mean_abs_m":road["mean_abs_m"],"road_rmse_m":road["rmse_m"],"road_worst_10":road.get("worst_10",[]),
             "refinement":p.get("refinement"),"raster_max_abs_m":p.get("raster_max_abs_m"),
             "library_error_m":p.get("library_error_m"),"target_error_m":p.get("target_error_m"),
             "distance_m":drive.get("distance_m"),"progress_m":drive.get("progress_m"),
             "road_name":drive.get("route",{}).get("name"),"road_way":drive.get("route",{}).get("way"),
             "road_grade_20m":drive.get("road_grade_20m"),"driven_heading_range_degrees":drive.get("driven_heading_range_degrees"),
             "contact_samples":drive.get("sample_count"),"contact_max_m":drive.get("contact_max_m"),
             "contact_mean_m":drive.get("contact_mean_m"),"surface_contact_max_m":drive.get("surface_contact_max_m"),
             "max_cross_track_m":drive.get("max_cross_track_m"),"collisions":drive.get("collisions"),
             "browser_success":b.get("success",False),"long_drive_success":drive.get("success",False),
             "multi_touch":b.get("multiTouch",False),"touch_release":b.get("touchRelease",False),
             "failure":b.get("error") or drive.get("reason")}
        if kind=="grid" and cell in (5,10):
            row["role"]="distant_lod"
            # LOD distance / thresholds still to tune on actual mobile hardware.
            row["rmse_budget_m"]=0.35 if cell==5 else 0.60
            row["pass"]=e["points"]==100 and e["rmse_m"]<=row["rmse_budget_m"]
        else:
            row["role"]="near_candidate"
            drive_ok=bool(row["browser_success"] and row["long_drive_success"]
                and t.get("kind")==kind and (kind=="tin" or t.get("cell")==cell)
                and t.get("source")=="DGT MDT 0.5 m" and row["multi_touch"] and row["touch_release"]
                and row["distance_m"] is not None and row["distance_m"]>=100
                and row["progress_m"] is not None and row["progress_m"]>=100
                and row["contact_samples"] is not None and row["contact_samples"]>=100
                and row["contact_max_m"] is not None and row["contact_max_m"]<=0.5
                and row["surface_contact_max_m"] is not None and row["surface_contact_max_m"]<=0.5
                and row["road_grade_20m"] is not None and row["road_grade_20m"]>=0.02
                and row["driven_heading_range_degrees"] is not None and row["driven_heading_range_degrees"]>=15
                and row["collisions"]==0)
            common_precision=bool(e["points"]==100 and e["max_abs_m"]<=0.5
                    and road["points"]>0 and road["max_abs_m"]<=0.5)
            row["precision_pass"]=common_precision and (
                (p["vertices"]<150000 and p["raster_max_abs_m"]<=0.5) if kind=="tin" else cell==2)
            compact_required=kind=="tin" and manifest.get("compact_tin_required",False)
            row["compression_pass"]=(p.get("encoding")=="MSLTERR1/compact" and p.get("exact_float32_geometry") is True and 0<(p.get("gzip_bytes") or 0)<1000000) if compact_required else None
            row["pass"]=row["precision_pass"] and drive_ok and (row["compression_pass"] if compact_required else True)
        rows.append(row)
    near=next((r for r in rows if r["kind"]=="tin" and r["pass"]),None)
    if near is None:
        near=next((r for r in rows if r["kind"]=="grid" and r["cell_m"]==2 and r["pass"]),None)
    passed=near is not None and manifest["coverage"]["invalid_pixels"]==0
    return {"schema":3,"tested_commit":os.getenv("GITHUB_SHA"),"branch":os.getenv("GITHUB_REF_NAME"),
            "run_id":os.getenv("GITHUB_RUN_ID"),"source_release":manifest["source_release"],
            "source_crs":manifest["source_crs"],"coverage_pixels":manifest["coverage"]["pixels_checked"],
            "invalid_pixels":manifest["coverage"]["invalid_pixels"],
            "inputs":[{k:a[k] for k in ("name","bytes","sha256")} for a in manifest["inputs"]],
            "tin_failure":manifest.get("tin_failure"),"results":rows,
            "recommended_default_file":near["file"] if passed else None,
            "recommended_default_kind":near["kind"] if passed else None,
            "recommended_default_cell_m":near["cell_m"] if passed else None,
            "pass":passed}

def finalize_manifest(manifest, report, terrain_dir):
    """Verify selected bytes, materialize alias, and align manifest with final gate."""
    if manifest.get("schema") != 2:
        raise ValueError("Expected conversion manifest schema 2")
    alias=terrain_dir/"terrain-default.bin"
    alias.unlink(missing_ok=True)
    # Clean legacy misnamed binary alias, not an original dataset.
    (terrain_dir/"terrain-default.json").unlink(missing_ok=True)
    selected=None
    if report["pass"]:
        filename=report["recommended_default_file"]
        if filename not in ("terrain-tin.bin","terrain-2m.bin"):
            raise ValueError("Unexpected selected terrain filename")
        row=next((r for r in report["results"] if r["file"]==filename and r["pass"]),None)
        if row is None:
            raise ValueError("Missing passing selected candidate")
        source=terrain_dir/filename
        with source.open("rb") as f:
            digest=hashlib.file_digest(f,"sha256").hexdigest()
        if digest!=row["sha256"] or source.stat().st_size!=row["raw_bytes"]:
            raise ValueError("Selected terrain hash/size mismatch")
        shutil.copyfile(source,alias)
        selected={"file":filename,"alias":alias.name,"kind":row["kind"],
                  "cell_m":row["cell_m"],"sha256":digest,"bytes":row["raw_bytes"]}
    return {**manifest,"validation_status":"passed" if report["pass"] else "failed",
            "final_pass":report["pass"],"default":selected,
            "validation_run_id":report["run_id"],"validation_commit":report["tested_commit"]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--terrain",type=Path,required=True)
    ap.add_argument("--browser",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    manifest_path=a.terrain/"manifest.json"
    manifest=json.loads(manifest_path.read_text())
    report=summarize(manifest,a.browser)
    final=finalize_manifest(manifest,report,a.terrain)
    tmp=manifest_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(final,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    tmp.replace(manifest_path)
    a.output.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,allow_nan=False))
    print(json.dumps({k:final[k] for k in ("grid_candidate_precision_pass","validation_status","final_pass","default")},allow_nan=False))
    return 0 if report["pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
