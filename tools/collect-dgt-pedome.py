#!/usr/bin/env python3
"""Collect DGT data for the expanded Pedome area using the normal authenticated STAC API.
Preserve originals and a provenance manifest. No credentials or signed URLs in output."""
import argparse, hashlib, importlib.util, json, re, time
from pathlib import Path
from urllib.parse import urlsplit
import requests

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("dgt",HERE/"download-dgt-pedome.py")
dgt=importlib.util.module_from_spec(spec);spec.loader.exec_module(dgt)
BBOX=[-8.405,41.405,-8.375,41.435]
COLLECTIONS=["MDT-50cm","MDS-50cm","MDT-2m","MDS-2m","LAZ","ORTOS-2025"]
LICENSE_SOURCE="https://www.dgterritorio.gov.pt/descarregamento-de-dados-lidar-de-portugal-continental"
ORTHO_SOURCE="https://www.dgterritorio.gov.pt/novo-catalogo-de-ortofotos-de-portugal-continental-no-centro-de-dados-da-dgt"
TIFF=(b"II*\x00",b"MM\x00*",b"II+\x00",b"MM\x00+")

def search(s,c):
    r=s.post(dgt.API+"/search",json={"bbox":BBOX,"collections":[c],"limit":1000},timeout=45)
    r.raise_for_status()
    body=r.json();v=body.get("data",body)
    fs=v.get("features")
    if not isinstance(fs,list):raise ValueError("Invalid STAC result")
    ctx=v.get("context",{})
    if ctx.get("matched",len(fs))>len(fs):raise ValueError("Incomplete STAC result")
    if not fs:raise ValueError("No matching items")
    return fs

def fetch(s,url,path,ext):
    if urlsplit(url).scheme!="https" or urlsplit(url).hostname not in dgt.ASSET_HOSTS|dgt.DOWNLOAD_HOSTS:
        raise ValueError("Unexpected asset origin")
    tmp=path.with_suffix(path.suffix+".part")
    for attempt in range(3):
        try:
            with s.get(url,stream=True,timeout=(20,120)) as r:
                r.raise_for_status()
                if urlsplit(r.url).scheme!="https" or urlsplit(r.url).hostname not in dgt.DOWNLOAD_HOSTS:
                    raise ValueError("Unexpected redirect host")
                chunks=r.iter_content(1024*1024)
                first=next(chunks,b"")
                if (ext==".tif" and first[:4] not in TIFF) or (ext==".laz" and first[:4]!=b"LASF"):
                    raise ValueError("Invalid file signature")
                size=len(first);h=hashlib.sha256(first)
                with tmp.open("wb") as f:
                    f.write(first)
                    for chunk in chunks:
                        f.write(chunk);h.update(chunk);size+=len(chunk)
                length=r.headers.get("Content-Length")
                if length and not r.headers.get("Content-Encoding") and size!=int(length):
                    raise ValueError("Incomplete file")
            tmp.replace(path)
            return size,h.hexdigest()
        except requests.RequestException:
            if attempt==2:raise
            time.sleep(3*(attempt+1))
        finally:
            tmp.unlink(missing_ok=True)

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
    p.add_argument("--collection",action="append",choices=COLLECTIONS)
    p.add_argument("--historical-orthos",action="store_true",help="Enumerate earlier orthophoto collections from the official catalogue")
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    result={"bbox":BBOX,"attribution":"Direção-Geral do Território (DGT)","license_policy_sources":[LICENSE_SOURCE,ORTHO_SOURCE],"items":[],"errors":[]}
    def save():
        (a.output/"manifest.json").write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    with requests.Session() as s:
        s.headers["User-Agent"]="MapSlop DGT data importer/0.2"
        dgt.login(s)
        selected=a.collection or COLLECTIONS
        if a.historical_orthos:
            response=s.get(dgt.API+"/collections",timeout=60)
            response.raise_for_status()
            body=response.json()
            catalog=body.get("data",body).get("collections",[])
            selected=[]
            for c in catalog:
                ident=c.get("id","")
                label=ident+" "+str(c.get("title",""))
                if re.fullmatch(r"[A-Za-z0-9_.-]+",ident) and re.search(r"orto",label,re.I) and re.search(r"1995|2004|2006|2007|2010|2012|2015|2018|2021",label) and "2025" not in ident:
                    selected.append(ident)
            selected=sorted(set(selected))
            print("Historical orthophoto collections:",selected,flush=True)
            if not selected:raise ValueError("Historical collections not found")
            result["selected_collections"]=selected
        for c in selected:
            try:
                features=search(s,c); print("Collection:",c,len(features),"items",flush=True)
                seen=set()
                for item in features:
                    ident=item.get("id","")
                    if item.get("collection")!=c or not re.fullmatch(r"[A-Za-z0-9_.-]+",ident):raise ValueError("Unexpected item ID")
                    version=str(item.get("properties",{}).get("version") or "")
                    if version and not version.isdigit():raise ValueError("Invalid version")
                    ext=".laz" if c=="LAZ" else ".tif"
                    candidates=[v for v in item.get("assets",{}).values() if v.get("href") and (("laz" in v.get("type","").lower() or "las" in v.get("type","").lower() or urlsplit(v["href"]).path.lower().endswith(".laz") or c=="LAZ") if c=="LAZ" else v.get("type","").startswith("image/tiff"))]
                    entry={"collection":c,"id":ident,"version":version,"bbox":item.get("bbox"),"ok":False}
                    if ident in seen:continue
                    seen.add(ident)
                    try:
                        if len(candidates)!=1:raise ValueError("Ambiguous or absent asset")
                        name=ident+("_v"+version.zfill(2) if version else "")+ext
                        path=a.output/name
                        size,digest=fetch(s,candidates[0]["href"],path,ext)
                        entry.update(ok=True,filename=name,bytes=size,sha256=digest)
                        print("OK",name,size,flush=True)
                    except Exception as e:
                        entry["error"]=type(e).__name__
                        if isinstance(e,requests.HTTPError):entry["http_status"]=e.response.status_code
                        elif isinstance(e,ValueError):entry["reason"]=str(e)
                        print("FAILED",ident,entry["error"],entry.get("http_status",""),entry.get("reason",""),flush=True)
                    result["items"].append(entry);save()
            except Exception as e:
                result["errors"].append({"collection":c,"error":type(e).__name__})
                print("Collection failed:",c,type(e).__name__,flush=True);save()
    save()
    return 0 if result["items"] and not result["errors"] and all(i["ok"] for i in result["items"]) else 1
if __name__=="__main__":raise SystemExit(main())
