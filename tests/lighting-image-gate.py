#!/usr/bin/env python3
"""Check synthetic shadow-only comparison; not a subjective visual approval."""
import json,sys
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
root=Path(sys.argv[1])
def load(name):return Image.open(root/(name+".png")).convert("RGB")
a,b=load("low"),load("low-shadow-disabled")
if a.size!=b.size:raise ValueError("Mismatched capture sizes")
w,h=a.size
# Luminance, central/lower scene (exclude UI and sky where possible).
a=a.crop((w//8,h//3,w-w//8,h-15)).convert("L")
b=b.crop((w//8,h//3,w-w//8,h-15)).convert("L")
n=a.width*a.height
pairs=list(zip(a.getdata(),b.getdata()))
dark=sum(y-x>=8 for x,y in pairs);bright=sum(x-y>=8 for x,y in pairs)
contrast=ImageStat.Stat(a).stddev[0]
r={"data_kind":"synthetic","darkened_pixels":dark,"brightened_pixels":bright,"region_pixels":n,"contrast":contrast,"pass":contrast>=5 and dark>=max(50,int(n*.001)) and dark>bright}
(root/"image-gate.json").write_text(json.dumps(r,indent=2))
print("LIGHTING_IMAGE_GATE",json.dumps(r))
if not r["pass"]:raise SystemExit("No confirmed visible shadow darkening")
