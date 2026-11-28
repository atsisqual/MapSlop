#!/usr/bin/env python3
"""Fail closed on the exact reviewed combined pilot archive; never publish raw source data."""
import hashlib,json,sys,tarfile
from pathlib import Path,PurePosixPath
TERRAIN="36019dfc27584d667555c794350107c29981da4f4ee15bac2c03078aba0d895b"
def require(ok,msg):
    if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(root,out):
    r=json.loads((root/"combined-report.json").read_text())
    require(r["pass"] is True and all(r["checks"].values()),"Combined run did not pass")
    c=r["candidate"];b=c["scene"]["buildings"]
    require(b["buildings"]==527 and b["measured"]==17 and not b["foundation_failures"],"Buildings not approved")
    require(c["scene"]["roof_counts"]=={"gray":214,"terracotta":294,"unknown":2},"Roof colours not approved")
    require(c["drive"]["success"] and c["drive"]["collisions"]==0 and c["drive"]["progress_m"]>=104,"Drive not approved")
    require(all(v["vegetation"]["total"]==5702 for v in c["captures"]),"Vegetation not approved")
    seen=set()
    with tarfile.open(root/"combined-runtime.tar.gz","r:gz") as t:
        members=t.getmembers()
        require(sum(m.size for m in members)<100_000_000,"Archive too large")
        for m in members:
            p=PurePosixPath(m.name)
            require(not p.is_absolute() and ".." not in p.parts and m.name not in seen,"Unsafe or duplicate member")
            seen.add(m.name)
            require(m.isdir() or m.isfile(),"Non-regular archive entry")
            require(p.parts and (p.parts[0] in {"js","ortho"} or m.name in {"index.html","build-report.json"}),"Unexpected archive root")
            if m.isfile():
                require(m.name in {"index.html","build-report.json","js/terrain.bin"} or p.parts[0]=="js" and p.suffix in {".js",".mjs"} or p.parts[0]=="ortho" and (p.suffix==".webp" or m.name=="ortho/manifest.json"),"Unexpected runtime extension: "+m.name)
        t.extractall(out,filter="data")
    require(sha(out/"js/terrain.bin")==TERRAIN,"TIN differs")
    build=json.loads((out/"build-report.json").read_text())
    require(build["buildings"]==527 and build["estimatedBuildings"]==156 and build["roads"]==179,"Build report differs")
    src=(out/"js/nairobi-geodata.js").read_text()
    geo,_=json.JSONDecoder().raw_decode(src.split("export const GEO = ",1)[1])
    require(len(geo["buildings"])==527 and sum(bool(b.get("est")) for b in geo["buildings"])==156,"Runtime heights differ")
    require(len(geo["roofColors"])==527 and len(geo["explicitPaving"]["sidewalks"])==19,"Missing visual corrections")
    trees,_=json.JSONDecoder().raw_decode((out/"js/pedome-trees.mjs").read_text().split("export const trees=",1)[1])
    require(len(trees)==5702,"Wrong tree count")
    manifest=json.loads((out/"ortho/manifest.json").read_text())
    require(manifest["terrain_sha256"]==TERRAIN and len(manifest["tiles"])==64,"Wrong orthophoto extent")
    expected={"manifest.json"}
    for tile in manifest["tiles"]:
        for d in tile["levels"].values():
            p=out/"ortho"/d["path"];require(p.name==d["path"] and p.stat().st_size==d["bytes"] and sha(p)==d["sha256"],"Bad tile")
            expected.add(d["path"])
    require({p.name for p in (out/"ortho").iterdir()}==expected,"Unexpected tile files")
    print("Approved combined runtime: 527 buildings (371 real heights, 156 estimated), 17 Roofer, 5702 trees, 64 orthophoto tiles")
    print("Runtime archive SHA256:",sha(root/"combined-runtime.tar.gz"))
if __name__=="__main__":main(Path(sys.argv[1]),Path(sys.argv[2]))
