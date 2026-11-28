#!/usr/bin/env python3
"""Verify a specifically authorized church + lighting pair and overlay only exact tested runtime files.
No network access, no archive extraction to arbitrary paths, no automatic approval."""
import argparse,hashlib,json,tarfile,re
from pathlib import Path
BASE="36019dfc27584d667555c794350107c29981da4f4ee15bac2c03078aba0d895b"
CHURCH_FILES={"js/pedome.js","js/pedome-buildings-detail.mjs","models/church.glb"}
LIGHT_FILES={"js/pedome.js","js/pedome-lighting.mjs"}
def require(ok,msg):
    if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read_report(root,entry,name):
    p=root/name
    require(re.fullmatch(r"[0-9a-f]{64}",entry["assets"][name]) and sha(p)==entry["assets"][name],"Unapproved report: "+name)
    return json.loads(p.read_text())
def patch_bytes(root,entry,name,expected):
    p=root/name
    require(sha(p)==entry["assets"][name],"Unapproved archive: "+name)
    out={}
    with tarfile.open(p,"r:gz") as tar:
        for m in tar:
            require(m.isfile() and m.name in expected and m.name not in out,"Unexpected archive member: "+m.name)
            require(0<m.size<=100_000_000,"Invalid runtime file size")
            out[m.name]=tar.extractfile(m).read()
    require(set(out)==expected,"Missing runtime members")
    return out
def passed(r):return r.get("pass") is True and all(v is True for v in r.get("checks",{}).values())
def verify(lock,church_root,light_root,runtime):
    require(lock.get("schema")==1 and lock.get("owner_reviewed") is True,"Explicit owner-approved lock required")
    c,l=lock["church"],lock["lighting"]
    require(re.fullmatch(r"geodata-dgt-local-church-[0-9]+-[0-9]+",c["tag"]) and re.fullmatch(r"geodata-pedome-lighting-[0-9]+-[0-9]+",l["tag"]),"Invalid release tags")
    require(sha(runtime/"js/terrain.bin")==BASE,"Wrong terrain")
    cr=read_report(church_root,c,"church-report.json")
    cg=read_report(church_root,c,"church-in-game-report.json")
    viewer=read_report(church_root,c,"viewer-report.json")
    lr=read_report(light_root,l,"lighting-report.json")
    visual=read_report(light_root,l,"lighting-visual-diagnostics.json")
    require(all(passed(r) for r in (cr,cg,viewer,lr,visual)),"One or more gates not approved")
    require(cr.get("fixture") is False and cr.get("osm_id")==149406360 and cr["holdout_rmse_m"]<=.4317902658049366+1e-5 and abs(cr["bounds"][1][1]-20.881288115940958)<=.02,"Church geometry regressed")
    require(cr["roof_selection"]["approved_v1_reproduced"] is True,"V1 verification missing")
    require(cr["optimization"]["geometry_uv_materials_unchanged"] is True and cr["optimization"]["decoded_pixels_unchanged"] is True,"Optimization gate missing")
    model=cr["glb_sha256"]
    require(cg["candidate"]["scene"]["church"]["sha256"]==model,"Church game test did not load approved GLB")
    for variant in ("baseline","candidate"):
        scene=lr[variant]["scene"]
        require(scene.get("church") and scene["church"]["sha256"]==model,"Lighting not tested with exact church")
        d=lr[variant]["drive"]
        require(d["success"] and d["collisions"]==0 and d["progress_m"]>=104,"Lighting drive gate failed")
    require(lr["checks"].get("same_church") is True and lr["checks"].get("tree_shadows") is True and visual["tree_shadow"]["darkened_by_8"]>0,"Missing combined visual gates")
    require({v["name"] for v in lr["candidate"]["captures"]}>={"mata","igreja-zoom","igreja-fachada","rua-das-boucas"},"Missing fixed camera evidence")
    cb=patch_bytes(church_root,c,"church-runtime-patch.tar.gz",CHURCH_FILES)
    lb=patch_bytes(light_root,l,"lighting-runtime-patch.tar.gz",LIGHT_FILES)
    require(hashlib.sha256(cb["models/church.glb"]).hexdigest()==model,"Model patch differs")
    require(model.encode() in lb["js/pedome.js"] and b"installLighting" in lb["js/pedome.js"],"Final shell does not bind the approved church")
    # Combined lighting shell must derive from the tested church shell.
    require(l.get("input_church_shell_sha256")==hashlib.sha256(cb["js/pedome.js"]).hexdigest(),"Church shell binding mismatch")
    require(l.get("input_church_model_sha256")==model,"Church model binding mismatch")
    combined={**cb,**lb}
    require({k:hashlib.sha256(v).hexdigest() for k,v in combined.items()}==lock["runtime_sha256"],"Final runtime hash mismatch")
    for rel,data in combined.items():
        p=runtime/rel
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(data)
    print("CHURCH_LIGHTING_LOCK_PASS",json.dumps({"church":c["tag"],"lighting":l["tag"],"model":model,"files":list(combined)}))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("lock",type=Path);p.add_argument("church",type=Path);p.add_argument("lighting",type=Path);p.add_argument("runtime",type=Path);a=p.parse_args()
    verify(json.loads(a.lock.read_text()),a.church,a.lighting,a.runtime)
