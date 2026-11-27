#!/usr/bin/env python3
"""Acquire open DGT vector layers for Pedome and neighbours. Keep sources separate."""
import argparse, json, hashlib, re
from pathlib import Path
from urllib.parse import urljoin,urlsplit
import requests
BASE="https://ogcapi.dgterritorio.gov.pt"
BBOX="-8.405,41.405,-8.375,41.435"
KNOWN=["freguesias","cos2025v1"]
def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    manifest={"bbox":BBOX,"source":BASE,"attribution":"Direção-Geral do Território (DGT)","license_policy":"https://www.dgterritorio.gov.pt/dados-abertos","layers":[]}
    with requests.Session() as s:
        s.headers["User-Agent"]="MapSlop/0.2 geographic data acquisition"
        def get(url,params=None):
            if urlsplit(url).scheme!="https" or urlsplit(url).hostname!="ogcapi.dgterritorio.gov.pt":raise ValueError("Unexpected host")
            r=s.get(url,params=params,timeout=90);r.raise_for_status();return r.json()
        catalog=get(BASE+"/collections",{"f":"json"})
        collections=catalog.get("collections",[])
        meta=[{"id":c.get("id"),"title":c.get("title"),"description":c.get("description"),"license":c.get("license")} for c in collections]
        (a.output/"ogc-collection-inventory.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2))
        print("Collections:",len(meta))
        # Do not collect ownership, address/person records or unrelated national datasets.
        targets=set(KNOWN)
        for c in meta:
            ident=c.get("id") or "";title=str(c.get("title") or "")
            if re.search(r"constru[cç]|edif[ií]cio|crus|cadastro predial|municipios|municípios",ident+" "+title,re.I):
                if re.search(r"histor|202[0-4]|201[0-9]|199[0-9]|propriet|titular|pessoa",ident+" "+title,re.I):continue
                if re.fullmatch(r"[A-Za-z0-9_.-]+",ident):targets.add(ident)
        # Limit exploratory collection count; known layers first.
        for ident in KNOWN+sorted(targets-set(KNOWN))[:12]:
            info={"collection":ident,"ok":False}
            try:
                source=BASE+"/collections/"+ident+"/items"
                response=get(source,{"bbox":BBOX,"limit":1000,"f":"json"})
                seen=set();features=[];matched=response.get("numberMatched")
                page=response
                for i in range(100):
                    for f in page.get("features",[]):
                        if not f.get("geometry"):continue
                        fid=str(f.get("id") or json.dumps(f["geometry"],sort_keys=True))
                        if fid in seen:continue
                        seen.add(fid)
                        if ident in KNOWN:
                            features.append(f)
                        else:
                            # Geometry only for exploratory cadastral/construction/land-use layers.
                            # No cadastral owner identifiers or personal attributes.
                            features.append({"type":"Feature","geometry":f["geometry"],"properties":{}})
                    nexturl=next((l.get("href") for l in page.get("links",[]) if l.get("rel")=="next"),None)
                    if not nexturl:break
                    page=get(urljoin(source,nexturl))
                else:raise ValueError("Pagination limit")
                if isinstance(matched,int) and len(features)!=matched:raise ValueError("Incomplete result")
                filename=ident+".geojson"
                doc={"type":"FeatureCollection","attribution":"Direção-Geral do Território (DGT)","source":source,"bbox_query":BBOX,"features":features}
                path=a.output/filename;path.write_text(json.dumps(doc,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
                info.update(ok=True,count=len(features),filename=filename,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
                print("OK",ident,len(features),flush=True)
            except Exception as e:
                info["error"]=type(e).__name__
                if isinstance(e,requests.HTTPError):info["status"]=e.response.status_code
                print("FAILED",ident,info["error"],info.get("status",""),flush=True)
            manifest["layers"].append(info)
            (a.output/"vector-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    return 0 if all(next((x["ok"] for x in manifest["layers"] if x["collection"]==c),False) for c in KNOWN) else 1
if __name__=="__main__":raise SystemExit(main())
