#!/usr/bin/env python3
"""MapSlop: standalone DGT public STAC client, with optional normal account login.
Protocol documented by DGT CDD Downloader 0.3.1 (qgispt/dgtcd_downer).
No QGIS or embedded credentials required. No login bypass.
"""
import argparse
import getpass
import os
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import requests

BASE = "https://cdd.dgterritorio.gov.pt"
API = BASE + "/dgt-be/v1"
AUTH = "https://auth.cdd.dgterritorio.gov.pt"
AUTH_PATH = AUTH + "/realms/dgterritorio/protocol/openid-connect/auth"
ASSET_HOSTS = {"cdd.dgterritorio.gov.pt", "stratus.d.incd.pt"}
# Observed legitimate authenticated DGT redirect to ACNCA object storage.
DOWNLOAD_HOSTS = ASSET_HOSTS | {"stor-002.a.acnca.pt", "stor-001.a.acnca.pt"}
TILES = ("178494", "178495", "179494", "179495")
ITEMS = [(c, f"{c}-{n}-07-2025") for c in ("MDT-50cm", "MDS-50cm") for n in TILES]
ITEMS += [("ORTOS-2025", f"ORTOS-2025-cog-25cm-{n}") for n in ("084-4", "084-2")]

class LoginForm(HTMLParser):
    def __init__(self):
        super().__init__()
        self.action = None
        self.hidden = {}
        self.active = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form":
            self.active = a.get("id") == "kc-form-login"
            if self.active:
                self.action = a.get("action")
        if self.active and tag == "input" and a.get("type") == "hidden" and a.get("name"):
            self.hidden[a["name"]] = a.get("value", "")
    def handle_endtag(self, tag):
        if tag == "form":
            self.active = False

def login(session):
    session.get(BASE, timeout=30).raise_for_status()
    page = session.get(AUTH_PATH, params={"client_id":"aai-oidc-dgt","response_type":"code",
        "redirect_uri":BASE+"/auth/callback","scope":"openid profile email"}, timeout=30)
    page.raise_for_status()
    form = LoginForm()
    form.feed(page.text)
    if not form.action:
        raise RuntimeError("Formulário Keycloak não encontrado; usa o portal normal.")
    target = urljoin(page.url, form.action)
    if urlsplit(target).scheme != "https" or urlsplit(target).netloc != urlsplit(AUTH).netloc:
        raise RuntimeError("Destino de autenticação inesperado.")
    user = os.environ.get("DGT_USERNAME")
    pwd = os.environ.get("DGT_PASSWORD")
    if bool(user) != bool(pwd):
        raise RuntimeError("Configurar ambos os segredos DGT.")
    if not user:
        if not __import__("sys").stdin.isatty():
            raise RuntimeError("Segredos DGT em falta no ambiente.")
        user = input("Email/utilizador DGT: ")
        pwd = getpass.getpass("Palavra-passe DGT (não será gravada): ")
    result = session.post(target, data={**form.hidden,"username":user,"password":pwd},
        headers={"Origin":AUTH,"Referer":page.url}, timeout=45)
    result.raise_for_status()
    if urlsplit(result.url).netloc != urlsplit(BASE).netloc:
        raise RuntimeError("Login não concluído (credenciais, MFA ou confirmação pendente).")
    check = session.post(API+"/search",json={"bbox":[-8.395,41.4105,-8.383,41.4195],"limit":1},timeout=30)
    check.raise_for_status()
    if "json" not in check.headers.get("content-type",""):
        raise RuntimeError("Sessão não confirmada.")
    print("Login regressou ao portal; pesquisa STAC respondeu. Cookies de sessão DGT presentes:", any(c.name in ("auth_session","connect.sid") and c.domain.endswith("dgterritorio.gov.pt") for c in session.cookies))

def metadata(session, collection, item, searched=None):
    obj = (searched or {}).get(item)
    if obj is None:
        r = session.get(f"{API}/collections/{collection}/items/{item}",timeout=40)
        r.raise_for_status()
        body = r.json()
        obj = body.get("data",body)
    if obj.get("id") != item or obj.get("collection") != collection:
        raise ValueError("Metadados não correspondem ao item esperado.")
    asset = next((v for v in obj.get("assets",{}).values() if v.get("type","").startswith("image/tiff")),None)
    if not asset:
        raise ValueError("Sem asset GeoTIFF.")
    url = asset["href"]
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ASSET_HOSTS or parsed.username or parsed.password:
        raise ValueError("Servidor de ficheiros inesperado.")
    version = str(obj.get("properties",{}).get("version") or "")
    if version and not re.fullmatch(r"\d+",version):
        raise ValueError("Versão inesperada.")
    return obj, url, item+("_v"+version.zfill(2) if version else "")+".tif"

def download(session,url,dest):
    if dest.exists():
        with dest.open("rb") as f:
            if f.read(4) not in (b"II*\x00",b"MM\x00*",b"II+\x00",b"MM\x00+"):
                raise ValueError("Ficheiro existente não é TIFF; remove-o manualmente.")
        print("Já existe:",dest.name)
        return
    part=dest.with_suffix(".tif.part")
    try:
        with session.get(url,stream=True,timeout=(20,120)) as r:
            r.raise_for_status()
            if urlsplit(r.url).scheme != "https" or urlsplit(r.url).hostname not in DOWNLOAD_HOSTS:
                raise RuntimeError("Destino não autorizado pelo cliente: "+str(urlsplit(r.url).hostname)+"; tipo: "+r.headers.get("Content-Type","").split(";")[0])
            chunks=r.iter_content(1024*1024)
            first=next(chunks,b"")
            if first[:4] not in (b"II*\x00",b"MM\x00*",b"II+\x00",b"MM\x00+"):
                raise RuntimeError("Resposta não é TIFF; poderá exigir login.")
            length=len(first)
            with part.open("wb") as f:
                f.write(first)
                for chunk in chunks:
                    f.write(chunk)
                    length+=len(chunk)
            expected=r.headers.get("Content-Length")
            if expected and not r.headers.get("Content-Encoding") and length!=int(expected):
                raise IOError("Transferência incompleta.")
        part.replace(dest)
        print("Descarregado:",dest.name,length,"bytes")
    finally:
        if part.exists():
            part.unlink()

def main():
    p=argparse.ArgumentParser(description="Download seletivo da DGT para Pedome")
    p.add_argument("--output",type=Path,default=Path("DGT-Pedome"))
    p.add_argument("--login",action="store_true",help="Autenticar com a tua conta DGT")
    p.add_argument("--collection",choices=["MDT-50cm","MDS-50cm","ORTOS-2025"],action="append")
    p.add_argument("--metadata-only",action="store_true")
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    report=[]
    with requests.Session() as s:
        s.headers["User-Agent"]="MapSlop DGT data importer/0.1"
        if a.login:
            login(s)
        searched = {}
        if a.login:
            collections = a.collection or ["MDT-50cm","MDS-50cm","ORTOS-2025"]
            for c in collections:
                response = s.post(API+"/search",json={"bbox":[-8.395,41.4105,-8.383,41.4195],"limit":100,"collections":[c]},timeout=40)
                response.raise_for_status()
                payload = response.json()
                data = payload.get("data",payload)
                features = data.get("features",[])
                print("STAC POST:",c,len(features),"items")
                for feature in features:
                    if feature.get("collection")==c and feature.get("id"):
                        searched[feature["id"]]=feature
        for collection,item in ITEMS:
            if a.collection and collection not in a.collection:
                continue
            entry={"id":item,"collection":collection}
            try:
                obj,url,name=metadata(s,collection,item,searched)
                entry.update(bbox=obj["bbox"],version=obj.get("properties",{}).get("version"),filename=name)
                if not a.metadata_only:
                    dest=a.output/name
                    download(s,url,dest)
                    with dest.open("rb") as f:
                        entry["sha256"]=hashlib.file_digest(f,"sha256").hexdigest()
                    entry["bytes"]=dest.stat().st_size
                entry["ok"]=True
            except Exception as exc:
                # Avoid printing signed asset URLs, credentials or session cookies.
                entry["ok"]=False
                entry["error"]=type(exc).__name__
                if isinstance(exc, requests.HTTPError):
                    entry["http_status"]=exc.response.status_code
                elif isinstance(exc,(ValueError,RuntimeError)):
                    entry["message"]=str(exc)[:200]
                print("Falhou:",item,entry.get("http_status",entry.get("message",entry["error"])))
            report.append(entry)
            (a.output/"manifest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return 0 if report and all(x["ok"] for x in report) else 1

if __name__=="__main__":
    raise SystemExit(main())
