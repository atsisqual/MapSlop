#!/usr/bin/env python3
"""Overlay only the rendering hotfix on the checksum-verified combined runtime."""
from pathlib import Path
import shutil
import sys

root=Path(__file__).resolve().parent
js=Path(sys.argv[1])/'js'
entry=js/'pedome.js'
s=entry.read_text()
def patch(old,new):
    global s
    if s.count(old)!=1:
        raise ValueError('Unexpected archived runtime: '+old)
    s=s.replace(old,new,1)
patch("import { installPedomeUI } from './pedome-ui.js';",
      "import { installPedomeUI } from './pedome-ui.js';\nimport { rendererOptions,installRenderDiagnostics,improveDepth } from './pedome-render-diagnostics.mjs';")
patch("new THREE.WebGPURenderer({antialias:true,forceWebGL:!navigator.gpu||new URLSearchParams(location.search).has('webgl')})",
      "new THREE.WebGPURenderer(rendererOptions())")
patch("await renderer.init();","await renderer.init();const renderDiagnostics=await installRenderDiagnostics(renderer);")
patch("const camera=cameras.camera;","const camera=cameras.camera;improveDepth(camera,scene);")
patch("const spawn=roadSpawn(null,0,0);","window.mapslop.renderDebug=()=>renderDiagnostics(scene,ortho,camera); const spawn=roadSpawn(null,0,0);")
entry.write_text(s)
for name in ("pedome-orthophoto-preview.mjs","pedome-render-diagnostics.mjs"):
    shutil.copy2(root/name,js/name)
print("Android render overlay applied; archived TIN, images, buildings and vegetation unchanged")
