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
g=out/"js/ground.js"
source=g.read_text()
old="const painted=paintMap(); const pot=document.createElement('canvas'); pot.width=painted.width; pot.height=2**Math.round(Math.log2(painted.height)); pot.getContext('2d').drawImage(painted,0,0,pot.width,pot.height); const map = new THREE.CanvasTexture(pot);\n  map.colorSpace = THREE.SRGBColorSpace;\n  configureGroundTexture(map,renderer);"
if source.count(old)!=1:raise ValueError("Unexpected original ground texture")
g.write_text(source.replace(old,"const map = null; // private tiled preview: no giant procedural canvas"))
p=out/"js/pedome.js"
s=p.read_text()
def patch(old,new):
    global s
    if s.count(old)!=1:raise ValueError("Unexpected shell: "+old)
    s=s.replace(old,new)
patch("import { buildGround } from './ground.js';","import { buildGround } from './ground.js';\nimport { installOrthophoto } from './pedome-orthophoto-preview.mjs';")
patch("scene.add(buildGround(renderer));","const ground=buildGround(renderer);scene.add(ground);const ortho=await installOrthophoto(scene,ground,renderer);")
patch("window.mapslop={GEO,controllers,camera,world};","window.mapslop={GEO,controllers,camera,world,orthoPreview:{ortho,scene,renderer,renderDrive:async(dt,t)=>{cameras.update(dt,t);ortho.update(camera);renderer.render(scene,camera);ui.update(t*1000);await new Promise(r=>requestAnimationFrame(r));}}};")
patch("renderer.render(scene,camera);ui.update(now);","ortho.update(camera);renderer.render(scene,camera);ui.update(now);")
p.write_text(s)
p=out/"index.html"
s=p.read_text()
s=s.replace("DGT — MDT 0,5 m (uso experimental)","DGT — MDT 0,5 m + ortofoto 2025 · CC BY 4.0 · pré-visualização privada")
p.write_text(s)
