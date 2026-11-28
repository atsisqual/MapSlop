#!/usr/bin/env python3
"""Download only explicitly selected Poly Haven CC0 PBR maps for offline builds.
No runtime calls. Verify provider MD5, dimensions, bytes; record SHA256 and metadata.
"""
import argparse,hashlib,io,json,urllib.request,urllib.parse
from pathlib import Path
from PIL import Image
ASSETS={"granite":"granite_wall","plaster":"white_plaster_rough_01"}
MAPS={"base":("diff","diffuse","Diffuse"),"normal":("nor_gl","normal_gl","Normal (GL)"),"rough":("rough","roughness","Rough")}
def map_entry(data,aliases):
    for key in aliases:
        if key in data:
            return data[key]["1k"]["jpg"]
    raise ValueError("Missing map "+str(aliases)+"; API keys="+str(sorted(data)))
UA="MapSlop/1.0 (offline CC0 asset preparation; https://github.com/atsisqual/MapSlop)"
def get(url,limit):
    u=urllib.parse.urlsplit(url)
    if u.scheme!="https" or u.hostname not in {"api.polyhaven.com","dl.polyhaven.org","cdn.polyhaven.com","polyhaven.com"}:raise ValueError("Unapproved source host")
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":UA}),timeout=60) as r:
        if urllib.parse.urlsplit(r.geturl()).hostname not in {"api.polyhaven.com","dl.polyhaven.org","cdn.polyhaven.com","polyhaven.com"}:raise ValueError("Unexpected redirect")
        data=r.read(limit+1)
    if len(data)>limit:raise ValueError("Download exceeds limit")
    return data
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument("output",type=Path);p.add_argument("--lock",type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    report={"provider":"Poly Haven","license":"CC0-1.0","license_url":"https://polyhaven.com/license","api_terms":"https://polyhaven.com/our-api","assets":{}}
    lock=json.loads(a.lock.read_text()) if a.lock else None
    if lock:
        if lock["provider"]!="Poly Haven" or lock["license"]!="CC0-1.0":raise ValueError("Unapproved lock")
        for role,asset in ASSETS.items():
            e=lock["assets"][role]
            if e["asset"]!=asset or set(e["maps"])!=set(MAPS):raise ValueError("Unexpected lock entry")
            for key,m in e["maps"].items():
                if m["file"]!=role+"-"+key+".jpg":raise ValueError("Unexpected filename")
                raw=get(m["url"],int(m["bytes"]))
                if len(raw)!=m["bytes"] or sha(raw)!=m["sha256"] or hashlib.md5(raw).hexdigest()!=m["provider_md5"]:raise ValueError("Locked material hash mismatch")
                im=Image.open(io.BytesIO(raw));im.load()
                if im.format!="JPEG" or list(im.size)!=m["size_px"]:raise ValueError("Unexpected locked texture")
                (a.output/m["file"]).write_bytes(raw)
        for name in ("manifest.json","materials.lock.json"):(a.output/name).write_text(json.dumps(lock,indent=2)+"\n")
        print("PBR_LOCKED",json.dumps(lock));return
    for role,asset in ASSETS.items():
        files=get("https://api.polyhaven.com/files/"+asset,2_000_000);info=get("https://api.polyhaven.com/info/"+asset,2_000_000)
        (a.output/(asset+"-files.json")).write_bytes(files);(a.output/(asset+"-info.json")).write_bytes(info)
        data=json.loads(files);meta=json.loads(info)
        entry={"asset":asset,"url":"https://polyhaven.com/a/"+asset,"authors":meta.get("authors",{}),"dimensions":meta.get("dimensions"),"metadata_sha256":sha(info),"files_sha256":sha(files),"maps":{}}
        for key,kind in MAPS.items():
            d=map_entry(data,kind);raw=get(d["url"],4_000_000)
            if len(raw)!=d["size"] or hashlib.md5(raw).hexdigest()!=d["md5"]:raise ValueError("Provider checksum/size mismatch")
            im=Image.open(io.BytesIO(raw));im.load()
            if im.format!="JPEG" or im.size!=(1024,1024):raise ValueError("Unexpected texture format or dimensions")
            name=role+"-"+key+".jpg";(a.output/name).write_bytes(raw)
            entry["maps"][key]={"file":name,"url":d["url"],"bytes":len(raw),"sha256":sha(raw),"provider_md5":d["md5"],"size_px":list(im.size)}
        report["assets"][role]=entry
    (a.output/"manifest.json").write_text(json.dumps(report,indent=2)+"\n")
    (a.output/"materials.lock.json").write_text(json.dumps(report,indent=2)+"\n")
    print("PBR_SOURCES",json.dumps(report))
if __name__=="__main__":main()
