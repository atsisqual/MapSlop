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

def compare(report,geo):
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
    missing=sorted(expected.keys()-buildings.keys())
    result={"exported_buildings":len(buildings),"expected":len(expected),"matched":len(matched),
            "missing_count":len(missing),"missing_ids":missing,
            "max_export_height_error_m":max(errors.values()) if errors and all(math.isfinite(e) for e in errors.values()) else None,
            "mismatch_count":len(bad),"mismatches":bad[:20],
            "exported_id_examples":[b["id"] for b in geo["buildings"][:5]],
            "expected_id_examples":[r["osm_id"] for r in report["rows"][:5]]}
    result["pass"]=len(buildings)==report["building_count"]==527 and len(matched)==len(expected)>0 and not bad
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("report",type=Path);p.add_argument("geodata",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args()
    geo=json.loads(a.geodata.read_text().split("export const GEO = ",1)[1].split(";\nGEO.terrain",1)[0])
    result=compare(json.loads(a.report.read_text()),geo)
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,allow_nan=False),flush=True)
    if not result["pass"]:raise SystemExit("Building preview verification failed; see comparison diagnostics")

if __name__=="__main__":main()
