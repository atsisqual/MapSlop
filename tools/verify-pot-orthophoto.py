#!/usr/bin/env python3
"""Validate a regenerated POT pyramid against the immutable combined runtime before replacing tiles."""
import hashlib,json,math,sys
from pathlib import Path
from PIL import Image

def sha(p):
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def require(ok,msg):
    if not ok:raise ValueError(msg)
def verify(old,new):
    a=json.loads((old/"manifest.json").read_text())
    b=json.loads((new/"manifest.json").read_text())
    for k in ("schema","year","attribution","license","origin_lat_lon","terrain_sha256","world_extent","tile_m","gutter_m","cols","rows","sources","raster_metadata"):
        require(a[k]==b[k],"Changed approved orthophoto metadata: "+k)
    require(b.get("sampling")=="pot-v1" and b["source_metres_per_pixel"]==.25,"Missing POT provenance")
    require(len(a["tiles"])==len(b["tiles"])==64,"Tile count changed")
    expected={"far":64,"mid":128,"near":512}
    totals=dict.fromkeys(expected,0);files={"manifest.json"}
    span=b["tile_m"]+2*b["gutter_m"]
    for x,y in zip(a["tiles"],b["tiles"]):
        for k in ("i","j","bounds"):require(x[k]==y[k],"Changed tile extent: "+k)
        require(set(y["levels"])==set(expected),"Missing LOD")
        for l,n in expected.items():
            d=y["levels"][l];name=f'{y["i"]}-{y["j"]}-{l}-pot{n}.webp'
            require(d["path"]==name and name not in files,"Unexpected tile name")
            p=new/name;files.add(name)
            require(d["px"]==n and n&(n-1)==0 and d["mip_levels"]==n.bit_length(),"Non-POT dimensions")
            require(math.isclose(d["metres_per_pixel"],span/n,abs_tol=1e-12),"Incorrect gutter sampling")
            require(0<d["bytes"]<=262144 and p.stat().st_size==d["bytes"] and sha(p)==d["sha256"],"Bad tile SHA/size")
            require(d["sha256"]!=x["levels"][l]["sha256"],"Old tile reused")
            with Image.open(p) as im:
                require(im.format=="WEBP" and im.size==(n,n),"Wrong decoded image: "+name)
                im.load()
            totals[l]+=d["bytes"]
    require({p.name for p in new.iterdir()}==files,"Unexpected files in POT pyramid")
    require(totals==b["bytes_by_level"] and totals["far"]<=1_000_000,"Transfer budget")
    report={"pass":True,"tiles":len(b["tiles"]),"levels":expected,"metres_per_pixel":{l:span/n for l,n in expected.items()},"bytes_by_level":totals,"old_manifest_sha256":sha(old/"manifest.json"),"new_manifest_sha256":sha(new/"manifest.json"),"terrain_sha256":b["terrain_sha256"]}
    print("POT_PYRAMID",json.dumps(report,sort_keys=True))
    return report
if __name__=="__main__":
    report=verify(Path(sys.argv[1]),Path(sys.argv[2]))
    if len(sys.argv)>3:Path(sys.argv[3]).write_text(json.dumps(report,indent=2)+"\n")
