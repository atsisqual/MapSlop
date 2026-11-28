#!/usr/bin/env python3
"""Confirm actual visible canopy shadows; record old/new bias zoom without claiming aesthetic acceptance."""
import json,sys
from pathlib import Path
from PIL import Image,ImageStat
root=Path(sys.argv[1])
def pair(a,b):
    a,b=[Image.open(root/(x+".png")).convert("RGB") for x in (a,b)]
    if a.size!=b.size:raise ValueError("Mismatched screenshot sizes")
    w,h=a.size
    # Exclude HUD and image border.
    a,b=[i.crop((w//8,h//5,w-w//8,h-h//8)).convert("L") for i in (a,b)]
    diff=[int(y)-int(x) for x,y in zip(a.getdata(),b.getdata())]
    n=len(diff)
    return {"pixels":n,"darkened_by_8":sum(d>=8 for d in diff),"brightened_by_8":sum(d<=-8 for d in diff),"mean_abs_luma_delta":sum(abs(d) for d in diff)/n,"contrast":ImageStat.Stat(a).stddev[0]}
trees=pair("mata-after","mata-sem-sombra-copas")
bias=pair("igreja-zoom-after","igreja-zoom-bias-antigo")
result={"tree_shadow":trees,"bias_zoom":bias,"pass":trees["contrast"]>=5 and trees["darkened_by_8"]>=max(30,int(trees["pixels"]*.0005)) and trees["darkened_by_8"]>trees["brightened_by_8"],"visual_review_required":True,"note":"Old/new bias zoom is diagnostic; numerical delta does not prove absence of acne."}
(root/"lighting-visual-diagnostics.json").write_text(json.dumps(result,indent=2)+"\n")
print("LIGHTING_VISUAL_DIAGNOSTICS",json.dumps(result))
if not result["pass"]:raise SystemExit("No visible canopy-only shadow difference")
