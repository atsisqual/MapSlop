#!/usr/bin/env python3
"""Compare Telea, Navier-Stokes and an optional locally verified LaMa ONNX checkpoint.
Never download or execute an unreviewed model. Preserve all outside-mask pixels exactly.
"""
import argparse,hashlib,json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

def inpaint(image,mask,method,model=None):
    if image.ndim!=3 or image.shape[2]!=3 or mask.shape!=image.shape[:2] or mask.dtype!=bool or not mask.any() or mask.all():raise ValueError("Invalid RGB/mask")
    n,labels,stats,_=cv2.connectedComponentsWithStats(mask.astype(np.uint8),8)
    if any(int(r[4])>4096 or max(r[2:4])>128 for r in stats[1:]):raise ValueError("Only small object masks accepted")
    if method in ("telea","ns"):
        pred=cv2.inpaint(image,mask.astype(np.uint8)*255,3,cv2.INPAINT_TELEA if method=="telea" else cv2.INPAINT_NS)
    elif method=="lama":
        if model is None:raise ValueError("Verified LaMa checkpoint required")
        h,w=mask.shape
        if h>512 or w>512:raise ValueError("LaMa requires a local crop at most 512x512")
        ph=512-h;pw=512-w
        im=np.pad(image,((0,ph),(0,pw),(0,0)),mode="reflect");ma=np.pad(mask,((0,ph),(0,pw)),mode="constant")
        x=im.transpose(2,0,1)[None].astype(np.float32)/255.;m=ma[None,None].astype(np.float32)
        inputs={i.name:i for i in model.get_inputs()}
        if set(inputs)!={"image","mask"}:raise ValueError("Unexpected LaMa inputs")
        y=model.run(None,{"image":x,"mask":m})[0]
        if y.shape!=(1,3,512,512) or not np.isfinite(y).all():raise ValueError("Unexpected LaMa output")
        # Pinned Carve FP32 export returns RGB in the 0..255 range.
        if y.max()<=1.5 or y.max()>260 or y.min()<-5:raise ValueError("Unexpected LaMa output scale")
        pred=np.rint(np.clip(y[0].transpose(1,2,0),0,255)).astype(np.uint8)[:h,:w]
    else:raise ValueError("Unknown method")
    out=image.copy();out[mask]=pred[mask]
    return out

def compare(original,damaged,mask,method,model=None):
    out=inpaint(damaged,mask,method,model)
    d=out.astype(float)-original.astype(float)
    return out,{"method":method,"masked_mae":float(np.abs(d[mask]).mean()),"masked_rmse":float(np.sqrt(np.mean(d[mask]**2))),"unmasked_exact":bool(np.array_equal(out[~mask],damaged[~mask]))}

def main():
    p=argparse.ArgumentParser();p.add_argument("--image",type=Path,required=True);p.add_argument("--mask",type=Path,required=True);p.add_argument("--truth",type=Path);p.add_argument("--output",type=Path,required=True);p.add_argument("--checkpoint",type=Path);p.add_argument("--checkpoint-sha256");p.add_argument("--checkpoint-license")
    a=p.parse_args();image=np.array(Image.open(a.image).convert("RGB"));mask=np.array(Image.open(a.mask).convert("L"))>127
    truth=np.array(Image.open(a.truth).convert("RGB")) if a.truth else None
    methods=["telea","ns"];model=None
    if a.checkpoint:
        if not a.checkpoint_sha256 or not a.checkpoint_license or hashlib.sha256(a.checkpoint.read_bytes()).hexdigest()!=a.checkpoint_sha256:raise ValueError("Verified checkpoint hash and license required")
        if a.checkpoint.suffix.lower()!=".onnx":raise ValueError("Only ONNX checkpoint accepted; no pickle execution")
        import onnxruntime as ort
        options=ort.SessionOptions();options.intra_op_num_threads=2
        model=ort.InferenceSession(str(a.checkpoint),sess_options=options,providers=["CPUExecutionProvider"]);methods.append("lama")
    a.output.mkdir(parents=True,exist_ok=False);rows=[]
    for method in methods:
        out=inpaint(image,mask,method,model)
        r={"method":method,"unmasked_exact":bool(np.array_equal(out[~mask],image[~mask]))}
        if truth is not None:
            d=out[mask].astype(float)-truth[mask].astype(float);r.update(masked_mae=float(np.abs(d).mean()),masked_rmse=float(np.sqrt(np.mean(d*d))))
        Image.fromarray(out).save(a.output/(method+".png"));rows.append(r)
    report={"pass":all(r["unmasked_exact"] for r in rows),"methods":rows,"lama_status":"executed" if model is not None else "blocked_checkpoint_not_supplied","checkpoint_sha256":a.checkpoint_sha256,"checkpoint_license":a.checkpoint_license}
    (a.output/"inpaint-report.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report))
    if not report["pass"]:raise SystemExit(1)
if __name__=="__main__":main()
