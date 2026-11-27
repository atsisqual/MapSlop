#!/usr/bin/env python3
"""Synthetic-only building heights for CI browser integration; never DGT evidence."""
import argparse,json
from pathlib import Path
from shapely.geometry import Polygon
from terrain_binary import decode
from terrain_tin import TinSampler
from building_heights import key,digest
p=argparse.ArgumentParser()
p.add_argument("--footprints",type=Path,required=True)
p.add_argument("--terrain",type=Path,required=True)
p.add_argument("--output",type=Path,required=True)
a=p.parse_args()
f=json.loads(a.footprints.read_text())
t=decode(a.terrain.read_bytes())
if t["source"]!="SYNTHETIC TEST TERRAIN":raise ValueError("Synthetic fixture only")
s=TinSampler(t)
rows=[]
for b in f["buildings"]:
    r={"footprint_key":key(b),"method":"fallback","render_height_m":b["h"]}
    poly=Polygon(list(zip(b["ring"][::2],b["ring"][1::2])),[list(zip(h[::2],h[1::2])) for h in b.get("holes",[])])
    if poly.is_valid and not poly.is_empty and not(b.get("part") or b.get("podium") or b.get("minH")):
        base=min(s(x,z) for x,z in zip(b["ring"][::2],b["ring"][1::2]))
        probe=poly.representative_point()
        r.update(method="mds_mdt",render_height_m=6.5,roof_relative_m=base+6.5,probe_local_m=[probe.x,probe.y])
    rows.append(r)
a.output.write_text(json.dumps({"schema":1,"source":"SYNTHETIC TEST BUILDINGS","osm_sha256":f["osm_sha256"],"terrain_sha256":digest(a.terrain),"buildings":rows}))
