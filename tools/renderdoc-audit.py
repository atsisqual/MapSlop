#!/usr/bin/env python3
"""Offline replay diagnostics of a capture of our own game, not a map-data extractor.
Run using the Python interpreter corresponding to the installed RenderDoc bindings.
"""
import argparse,hashlib,json
from pathlib import Path

def audit(path,manifest):
    import renderdoc as rd
    m=json.loads(manifest.read_text())
    if m.get("source_type") not in ("own_mapslop_capture","synthetic_renderdoc_capture") or not m.get("reviewed_by") or m.get("sha256")!=hashlib.sha256(path.read_bytes()).hexdigest():raise ValueError("Own-game capture provenance required")
    cap=rd.OpenCaptureFile()
    try:
        result=cap.OpenFile(str(path),"",None)
        if result!=rd.ResultCode.Succeeded:raise RuntimeError(str(result))
        if cap.LocalReplaySupport()!=rd.ReplaySupport.Supported:raise RuntimeError("Capture cannot be replayed on this system")
        result,controller=cap.OpenCapture(rd.ReplayOptions(),None)
        if result!=rd.ResultCode.Succeeded:raise RuntimeError(str(result))
        try:
            roots=controller.GetRootActions();stack=list(roots);draws=0;actions=0
            while stack:
                a=stack.pop();stack.extend(a.children);actions+=1
                if a.flags&rd.ActionFlags.Drawcall:draws+=1
            textures=controller.GetTextures();buffers=controller.GetBuffers()
            return {"pass":draws>0,"source_type":m["source_type"],"actions":actions,"draws":draws,"textures":len(textures),"buffers":len(buffers),"texture_bytes":sum(t.byteSize for t in textures),"buffer_bytes":sum(b.length for b in buffers),"capture_sha256":m["sha256"]}
        finally:controller.Shutdown()
    finally:cap.Shutdown()
def main():
    p=argparse.ArgumentParser();p.add_argument("capture",type=Path);p.add_argument("manifest",type=Path);p.add_argument("output",type=Path);a=p.parse_args()
    r=audit(a.capture,a.manifest);a.output.write_text(json.dumps(r,indent=2)+"\n");print(json.dumps(r))
    if not r["pass"]:raise SystemExit(1)
if __name__=="__main__":main()
