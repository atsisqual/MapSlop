#!/usr/bin/env python3
"""Install the orthophoto preview only in a private, explicitly staged build."""
from pathlib import Path
import shutil
import sys

out=Path(sys.argv[1])
tiles=Path(sys.argv[2])
root=Path(__file__).resolve().parent
for name in ("orthophoto-partition.mjs","pedome-orthophoto-preview.mjs"):
    shutil.copy2(root/name,out/"js"/name)
shutil.copytree(tiles,out/"ortho")
p=out/"js/pedome.js"
s=p.read_text()
def patch(old,new):
    global s
    if s.count(old)!=1:raise ValueError("Unexpected shell: "+old)
    s=s.replace(old,new)
patch("import { buildGround } from './ground.js';","import { buildGround } from './ground.js';\nimport { installOrthophoto } from './pedome-orthophoto-preview.mjs';")
patch("scene.add(buildGround(renderer));","const ground=buildGround(renderer);scene.add(ground);const ortho=await installOrthophoto(scene,ground,renderer);")
patch("window.mapslop={GEO,controllers,camera,world};","window.mapslop={GEO,controllers,camera,world,orthoPreview:{ortho,scene,renderer}};")
patch("renderer.render(scene,camera);ui.update(now);","ortho.update(camera);renderer.render(scene,camera);ui.update(now);")
p.write_text(s)
p=out/"index.html"
s=p.read_text()
s=s.replace("DGT — MDT 0,5 m (uso experimental)","DGT — MDT 0,5 m + ortofoto 2025 · CC BY 4.0 · pré-visualização privada")
p.write_text(s)
