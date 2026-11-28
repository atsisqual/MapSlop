"""Two textured adjacent OBJ objects with same material, plus provenance."""
import argparse,hashlib,json
from pathlib import Path
from PIL import Image
p=argparse.ArgumentParser();p.add_argument("output",type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
(a.output/"fixture.obj").write_text("mtllib fixture.mtl\no left\nv 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nvt 1 0\nvt 0 1\nusemtl shared\nf 1/1 2/2 3/3\no right\nv 1 0 0\nv 1 1 0\nv 0 1 0\nusemtl shared\nf 4/2 5/1 6/3\n")
(a.output/"fixture.mtl").write_text("newmtl shared\nKd 1 1 1\nmap_Kd texture.png\n")
im=Image.new("RGB",(16,16));im.putdata([(255*(x//4%2),255*(y//4%2),80) for y in range(16) for x in range(16)]);im.save(a.output/"texture.png")
m={"source_type":"synthetic","license":"MIT","author":"MapSlop fixture","reviewed_by":"CI","source_url_or_archive":"tools/generate-obj-fixture.py","files":{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in a.output.iterdir()}}
(a.output/"manifest.json").write_text(json.dumps(m))
