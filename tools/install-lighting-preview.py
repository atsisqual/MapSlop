#!/usr/bin/env python3
"""Stage lighting only in a copy of the approved combined runtime."""
import argparse,hashlib,shutil
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument("runtime",type=Path);p.add_argument("output",type=Path);a=p.parse_args()
    if a.output.exists():raise ValueError("Refuse overwrite")
    shutil.copytree(a.runtime,a.output)
    root=Path(__file__).resolve().parent
    shutil.copy2(root/"pedome-lighting.mjs",a.output/"js/pedome-lighting.mjs")
    f=a.output/"js/pedome.js";s=f.read_text()
    def patch(old,new,n=1):
        nonlocal s
        if s.count(old)!=n:raise ValueError("Unexpected runtime anchor "+old)
        s=s.replace(old,new)
    patch("import { installPedomeUI } from './pedome-ui.js';","import { installPedomeUI } from './pedome-ui.js';\nimport { installLighting } from './pedome-lighting.mjs';")
    patch("window.mapslop={GEO,controllers,camera,world,","const lighting=installLighting(scene,renderer,sun,scene.children.find(o=>o.isHemisphereLight),buildingGroup,new URLSearchParams(location.search).get('quality')||'low');\n window.mapslop={GEO,controllers,camera,world,lighting,")
    patch("renderer.render(scene,camera);","lighting.update(camera);renderer.render(scene,camera);",2)
    f.write_text(s)
    changed=[str(p.relative_to(a.runtime)) for p in a.runtime.rglob("*") if p.is_file() and sha(p)!=sha(a.output/p.relative_to(a.runtime))]
    if changed!=["js/pedome.js"]:raise ValueError("Unexpected files changed "+str(changed))
    print("LIGHTING_INSTALL",changed)
if __name__=="__main__":main()
