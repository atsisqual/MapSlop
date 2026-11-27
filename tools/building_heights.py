"""Building height interchange, tied to exact rendered OSM footprints and terrain."""
import hashlib
import json
import math

def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()

def key(b):
    data=[b["osmType"],b["id"],b["ring"],b.get("holes",[])]
    return hashlib.sha256(json.dumps(data,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def apply(buildings,report,osm_sha,terrain_sha):
    if report.get("schema")!=1 or report.get("osm_sha256")!=osm_sha or report.get("terrain_sha256")!=terrain_sha:
        raise ValueError("Building report provenance mismatch")
    rows=report["buildings"]
    indexed={r["footprint_key"]:r for r in rows}
    keys=[key(b) for b in buildings]
    if len(set(keys))!=len(keys) or len(indexed)!=len(rows) or set(indexed)!=set(keys):
        raise ValueError("Building footprint mismatch/duplicate")
    count=0
    for b,k in zip(buildings,keys):
        r=indexed[k]
        if r["method"]=="mds_mdt":
            h=r["render_height_m"]
            roof=r["roof_relative_m"]
            if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (h,roof)) or not 1.5<=h<=80:
                raise ValueError("Invalid measured height")
            if b.get("part") or b.get("podium") or b.get("minH"):
                raise ValueError("Unsupported measured building part")
            b["h"]=h
            probe=r.get("probe_local_m")
            if not isinstance(probe,list) or len(probe)!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in probe):
                raise ValueError("Invalid building probe")
            b["heightSource"]="synthetic_mds_mdt" if report.get("source")=="SYNTHETIC TEST BUILDINGS" else "mds_mdt"
            b["roofProbe"]=probe
            b["roofTargetY"]=roof
            b.pop("est",None)
            count+=1
        elif r["method"]=="fallback":
            if r["render_height_m"]!=b["h"]:
                raise ValueError("Fallback changes original height")
            b["heightSource"]="osm_or_estimate"
        else:
            raise ValueError("Unknown building height method")
    return count
