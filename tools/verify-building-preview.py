import argparse
import json
import math
from pathlib import Path
import re

def osm_way_id(value):
    if type(value) is int and value>0:return value
    if isinstance(value,str):
        m=re.fullmatch(r"(?:way/)?([1-9][0-9]*)",value)
        if m:return int(m[1])
    raise ValueError(f"Unsupported OSM way identity: {value!r}")

def compare(report,geo,osm=None):
    # Explicit, source-backed exception for this pilot's S3DB roof outline.
    # The pinned exporter replaces an outline when an exported part centroid lies inside.
    exclusions={}
    if osm is not None:
        ways={e["id"]:e for e in osm["elements"] if e["type"]=="way"}
        outline=ways.get(1493951967,{})
        part=ways.get(1531621904,{})
        if outline.get("tags",{}).get("building")=="roof" and outline.get("tags",{}).get("layer")=="1" and part.get("tags",{}).get("building:part"):
            # Require the source part to share the roof boundary and be actually exported.
            if len(set(outline.get("nodes",[])) & set(part.get("nodes",[])))>=2:
                exclusions[1493951967]={"status":"excluded","reason":"s3db_outline_replaced_by_building_part","replacement_osm_id":1531621904}

    buildings={}
    for b in geo["buildings"]:
        key=osm_way_id(b["id"])
        if key in buildings:raise ValueError(f"Duplicate exported building {key}")
        buildings[key]=b
    expected={}
    for row in report["rows"]:
        if row.get("preview_policy")!="raster_p90_candidate":continue
        key=osm_way_id(row["osm_id"])
        if key in expected:raise ValueError(f"Duplicate expected building {key}")
        expected[key]=float(row["height_m"])
    matched=sorted(expected.keys() & buildings.keys())
    errors={i:abs(float(buildings[i]["h"])-expected[i]) for i in matched}
    bad=[{"osm_id":i,"expected_m":expected[i],"exported_m":buildings[i]["h"],"error_m":err}
         for i,err in errors.items() if not math.isfinite(err) or err>0.011]
    excluded=[{"osm_id":i,**exclusions[i]} for i in sorted(expected.keys()-buildings.keys())
              if i in exclusions and exclusions[i]["replacement_osm_id"] in buildings and buildings[exclusions[i]["replacement_osm_id"]].get("part")]
    missing=sorted(expected.keys()-buildings.keys()-{e["osm_id"] for e in excluded})
    result={"exported_buildings":len(buildings),"expected":len(expected),"matched":len(matched),
            "missing_count":len(missing),"missing_ids":missing,"excluded_count":len(excluded),"excluded":excluded,
            "max_export_height_error_m":max(errors.values()) if errors and all(math.isfinite(e) for e in errors.values()) else None,
            "mismatch_count":len(bad),"mismatches":bad[:20],
            "exported_id_examples":[b["id"] for b in geo["buildings"][:5]],
            "expected_id_examples":[r["osm_id"] for r in report["rows"][:5]]}
    result["pass"]=len(buildings)==report["building_count"]==527 and len(matched)+len(excluded)==len(expected)>0 and not bad
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--osm",type=Path,required=True);p.add_argument("report",type=Path);p.add_argument("geodata",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args()
    geo=json.loads(a.geodata.read_text().split("export const GEO = ",1)[1].split(";\nGEO.terrain",1)[0])
    result=compare(json.loads(a.report.read_text()),geo,json.loads(a.osm.read_text()))
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,allow_nan=False),flush=True)
    if not result["pass"]:raise SystemExit("Building preview verification failed; see comparison diagnostics")

if __name__=="__main__":main()
