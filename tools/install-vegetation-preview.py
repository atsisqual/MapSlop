#!/usr/bin/env python3
"""Private opt-in vegetation build; does not alter production build or Pages."""
import json
from pathlib import Path
import shutil
import sys

root=Path(__file__).resolve().parents[1]
out=Path(sys.argv[1])
data=Path(sys.argv[2])
trees=json.loads(data.read_text())["trees"]
if not trees: raise ValueError("No trees")
shutil.copy2(root/"tools/pedome-vegetation-preview.mjs",out/"js/pedome-vegetation-preview.mjs")
(out/"js/pedome-trees.mjs").write_text("export const trees="+json.dumps(trees,separators=(",",":"),allow_nan=False)+";\n")
p=out/"js/pedome.js"
s=p.read_text()
def patch(old,new):
    global s
    if s.count(old)!=1: raise ValueError("Unexpected shell: "+old)
    s=s.replace(old,new)
patch("import { installPedomeUI } from './pedome-ui.js';","import { installPedomeUI } from './pedome-ui.js';\nimport { installVegetation } from './pedome-vegetation-preview.mjs';\nimport { trees } from './pedome-trees.mjs';")
patch("const camera=cameras.camera;","const camera=cameras.camera; const vegetation=installVegetation(scene,trees);")
patch("window.mapslop={GEO,controllers,camera,world};","window.mapslop={GEO,controllers,camera,world,vegetationPreview:{vegetation,renderer,scene}};")
patch("renderer.render(scene,camera);ui.update(now);","vegetation.update(camera);renderer.render(scene,camera);ui.update(now);")
p.write_text(s)
