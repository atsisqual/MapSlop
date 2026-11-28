#!/usr/bin/env python3
"""Package tested static gameplay preview, not a deployment.
Only curated runtime paths, exact hashes; no source geodata, private inputs or credentials.
"""
import argparse,hashlib,json,zipfile
from pathlib import Path
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument("runtime",type=Path);p.add_argument("validation",type=Path);p.add_argument("output",type=Path);p.add_argument("--church-report",type=Path);a=p.parse_args()
    validation=json.loads(a.validation.read_text())
    if not validation["pass"] or not validation["checks"] or not all(validation["checks"].values()):raise ValueError("Gameplay gate not passed")
    if a.church_report:
        r=json.loads(a.church_report.read_text())
        if not r["pass"] or r["fixture"] or sha(a.runtime/"models/church.glb")!=r["glb_sha256"]:raise ValueError("Church candidate mismatch")
    # Explicit allowlist. Only browser runtime, not source archives or npm packages.
    files=[]
    for path in a.runtime.rglob("*"):
        if not path.is_file():continue
        rel=path.relative_to(a.runtime)
        if path.is_symlink():raise ValueError("Unexpected symlink")
        if (len(rel.parts)==1 and rel.name in {"index.html","build-report.json"}) or rel.parts[0] in {"js","ortho","models","vendor"}:
            if rel.suffix.lower() not in {".js",".mjs",".json",".html",".bin",".gz",".webp",".jpg",".jpeg",".png",".glb",".wasm",".txt",".md",".css",".map",".ktx2",".svg"} and rel.name not in {"LICENSE","LICENSE.txt"}:continue
            files.append((path,rel.as_posix()))
    for required in ("index.html","js/terrain.bin","js/pedome.js","ortho/manifest.json","vendor/three/build/three.module.js"):
        if required not in {r for _,r in files}:raise ValueError("Missing runtime file: "+required)
    if sum(p.stat().st_size for p,_ in files)>160_000_000:raise ValueError("Preview size limit")
    notice="MapSlop — PRIVATE TEST PREVIEW / não publicar\n\nExtrair ZIP e abrir terminal nessa pasta. Executar:\npython -m http.server 8080 --bind 127.0.0.1\nAbrir http://127.0.0.1:8080/mobile.html?webgl no browser.\nNa rede local: usar --bind 0.0.0.0 apenas numa rede de confiança e abrir o IP do computador no telemóvel; parar servidor no fim.\nDGT MDT/LiDAR/Ortofoto 2025 CC BY 4.0; OSM contributors ODbL; fachadas estimadas; materiais Poly Haven CC0 quando presentes. Atribuição em jogo e licenças de fornecedores incluídas.\n"
    inventory={r:sha(p) for p,r in files}
    with zipfile.ZipFile(a.output,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=5) as z:
        for path,rel in files:z.write(path,rel)
        z.writestr("mobile.html",(a.runtime/"index.html").read_bytes())
        z.writestr("README.txt",notice)
        z.writestr("preview-validation.json",a.validation.read_bytes())
        if a.church_report:z.writestr("church-report.json",a.church_report.read_bytes())
        z.writestr("SHA256SUMS.json",json.dumps(inventory,indent=2))
    with zipfile.ZipFile(a.output) as z:
        if z.testzip() is not None:raise ValueError("ZIP CRC")
    print("PLAYABLE_PREVIEW",json.dumps({"files":len(files),"bytes":a.output.stat().st_size,"sha256":sha(a.output),"validation":str(a.validation)}))
if __name__=="__main__":main()
