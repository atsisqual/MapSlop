"""Verify the exact owner-approved Pages terrain; no general gate waiver."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
from terrain_binary import decode

RAW_SHA="36019dfc27584d667555c794350107c29981da4f4ee15bac2c03078aba0d895b"
GZIP_SHA="9c5ec9ecd8aceb76908e915fffaac896930e6499379a1421af88d887cb8dd991"
RAW_BYTES=1579941
GZIP_BYTES=1039989
RUN=46085062868
# Owner-authorized release exception ONLY for this exact immutable SHA.
def verify(root):
    report=json.loads((root/"road-validation.json").read_text())
    storage=report["storage"];surface=report["surface"];carve=report["carve"]
    if (report.get("profile_pass") is not True or storage.get("exact_float32_geometry") is not True
        or storage.get("sha256")!=RAW_SHA or storage.get("gzip_sha256")!=GZIP_SHA
        or storage.get("bytes")!=RAW_BYTES or storage.get("gzip_bytes")!=GZIP_BYTES
        or carve.get("missing_mandatory_edges")!=0 or carve.get("vertices")!=126528):
        raise ValueError("Not the reviewed road derivative")
    def limit(key,maximum):
        v=surface[key]
        if not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=maximum:
            raise ValueError("Unexpected surface metric: "+key)
    for k,v in {"max_crossfall_degrees":1.928,"max_ramp_crossfall_degrees":1.928,
                "max_centre_mesh_profile_delta_m":.920,"max_centre_mesh_profile_delta_away_from_ramps_m":.1,
                "max_centre_mesh_target_delta_m":.1,"max_junction_mesh_delta_m":.02,
                "max_junction_platform_crossfall_degrees":1,"outside_max_change_m":.1,
                "near_berm_outside_max_change_m":.1,"dense_mesh_max_mdt_deviation_m":1,
                "dense_mesh_max_way_mean_mdt_deviation_m":.5}.items():limit(k,v)
    for name,allowed,window,raw,roll in (
        ("drive_acceptance_20kmh",{"surface_window_0_2s_absolute"},2.958,16.438,.429),
        ("drive_acceptance_50kmh",{"baseline_speed","candidate_speed"},3.600,19.424,.444)):
        d=report[name];checks=d["checks"]
        failed={k for k,v in checks.items() if v is not True}
        if failed!=allowed or set(d["failed_checks"])!=allowed or d.get("baseline_partial") is not False:
            raise ValueError("Unexpected drive failure predicates: "+name)
        for key,cap in (("surface_window_0_2s",window),("surface_raw",raw),("straight_roll_max_degrees",roll)):
            m=d["metrics"][key];v=m["candidate"];b=m["baseline"]
            if not all(isinstance(x,(int,float)) and math.isfinite(x) for x in (v,b)) or not 0<=v<=cap or not v<b:
                raise ValueError("Driving regression: "+key)
    raw=(root/"terrain-road-preview.bin").read_bytes()
    if len(raw)!=RAW_BYTES or hashlib.sha256(raw).hexdigest()!=RAW_SHA:
        raise ValueError("Unapproved terrain bytes")
    t=decode(raw)
    if t.get("kind")!="tin" or t.get("source")!="DGT MDT 0.5 m" or len(t["vertices"])//3!=126528:
        raise ValueError("Unexpected TIN metadata")
    compressed=gzip.compress(raw,compresslevel=9,mtime=0)
    if len(compressed)!=GZIP_BYTES or hashlib.sha256(compressed).hexdigest()!=GZIP_SHA:
        raise ValueError("Unapproved compressed terrain bytes")
    (root/"terrain-tin.bin").write_bytes(raw)
    (root/"terrain-tin.bin.gz").write_bytes(compressed)
    print("Verified owner-approved run",RUN,RAW_SHA,GZIP_SHA,flush=True)

if __name__=="__main__":
    verify(Path(sys.argv[1]))
