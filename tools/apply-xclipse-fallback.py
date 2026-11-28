#!/usr/bin/env python3
"""Minimal render-only fallback for the approved public combined runtime."""
from pathlib import Path
import sys

root=Path(sys.argv[1])/"js"
p=root/"pedome-orthophoto-preview.mjs"
s=p.read_text()
old="tex.colorSpace=THREE.SRGBColorSpace;tex.anisotropy=Math.min(8,renderer.getMaxAnisotropy?.()||4);"
new="""tex.colorSpace=THREE.SRGBColorSpace;tex.anisotropy=Math.min(8,renderer.getMaxAnisotropy?.()||4);
  const b=renderer.backend,q=new URLSearchParams(location.search);
  let gpu='';
  if(b.isWebGLBackend){const gl=b.gl,e=gl.getExtension('WEBGL_debug_renderer_info');gpu=String(gl.getParameter(e?e.UNMASKED_RENDERER_WEBGL:gl.RENDERER));}
  else gpu=JSON.stringify(b.device?.adapterInfo||{});
  if(q.get('mips')==='0'||/xclipse/i.test(gpu)){
    tex.generateMipmaps=false;tex.mipmapsAutoUpdate=false;tex.minFilter=THREE.LinearFilter;tex.magFilter=THREE.LinearFilter;tex.anisotropy=1;tex.needsUpdate=true;
  }
  tex.userData.mipMode=tex.generateMipmaps?'gpu':'0';"""
if s.count(old)!=1:raise ValueError("Unexpected archived ortho material")
p.write_text(s.replace(old,new,1))
print("Xclipse fallback: only disables terrain mipmaps/aniso on Xclipse or explicit mips=0; no other visual changes.")
