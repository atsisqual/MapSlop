#!/usr/bin/env python3
"""Run 3dfier on inventoried local polygons and LAS/LAZ in a digest-pinned offline container.
Fixture demonstrates semantic lifting; never overwrite approved game TIN.
"""
import argparse,hashlib,json,math,shutil,subprocess
from pathlib import Path
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()
def fixture(out):
    import laspy,numpy as np
    from pyproj import CRS
    out.mkdir(parents=True,exist_ok=False)
    x0,y0=-50000,180000
    def polygon(name,x1,y1,x2,y2):
        ring=[[x0+x,y0+y] for x,y in [(x1,y1),(x2,y1),(x2,y2),(x1,y2),(x1,y1)]]
        doc={"type":"FeatureCollection","crs":{"type":"name","properties":{"name":"urn:ogc:def:crs:EPSG::3763"}},"features":[{"type":"Feature","properties":{"id":name},"geometry":{"type":"Polygon","coordinates":[ring]}}]}
        (out/(name+".geojson")).write_text(json.dumps(doc))
    polygon("road",0,0,20,4);polygon("wall",0,4,20,4.6)
    x,y=np.meshgrid(np.arange(-1,21.01,.2),np.arange(-1,6.01,.2));x=x.ravel();y=y.ravel()
    z=100+.02*x;classes=np.full(len(x),2,np.uint8)
    # Ground class 2 and separation-top returns class 17, not claimed to be DGT classification.
    wx,wy=np.meshgrid(np.arange(.1,20,.2),np.arange(4.1,4.6,.2));wx=wx.ravel();wy=wy.ravel()
    x=np.r_[x,wx];y=np.r_[y,wy];z=np.r_[z,101.3+.02*wx];classes=np.r_[classes,np.full(len(wx),17,np.uint8)]
    header=laspy.LasHeader(point_format=3,version="1.2");header.offsets=[x0,y0,100];header.scales=[.001,.001,.001];header.add_crs(CRS.from_epsg(3763));las=laspy.LasData(header);las.x=x+x0;las.y=y+y0;las.z=z;las.classification=classes;las.return_number=np.ones(len(x),np.uint8);las.number_of_returns=np.ones(len(x),np.uint8);las.write(out/"points.las")
    (out/"config.yml").write_text("""input_polygons:
  - datasets:
      - /data/road.geojson
    uniqueid: id
    lifting: Road
  - datasets:
      - /data/wall.geojson
    uniqueid: id
    lifting: Separation
lifting_options:
  Road:
    height: percentile-50
    use_LAS_classes:
      - 2
  Separation:
    height: percentile-80
    use_LAS_classes:
      - 17
input_elevation:
  - datasets:
      - /data/points.las
    thinning: 1
options:
  radius_vertex_elevation: 1.0
  threshold_jump_edges: 0.5
""")
    (out/"manifest.json").write_text(json.dumps({"source_type":"synthetic","license":"MIT","crs":"EPSG:3763","files":{p.name:sha(p) for p in out.iterdir()}},indent=2))
def run(src,out,image):
    src=src.resolve();out=out.resolve()
    if not image.startswith("tudelft3d/3dfier@sha256:") or len(image.split(":")[-1])!=64:raise ValueError("Require official image digest")
    m=json.loads((src/"manifest.json").read_text())
    if m.get("crs")!="EPSG:3763" or not m.get("license") or "config.yml" not in m["files"]:raise ValueError("Explicit source CRS/license/config required")
    out.mkdir(parents=True,exist_ok=False);work=out/"input";work.mkdir()
    for name,digest in m["files"].items():
        if Path(name).name!=name or sha(src/name)!=digest:raise ValueError("Input manifest mismatch")
        shutil.copy2(src/name,work/name)
    work.chmod(0o777)
    args=["docker","run","--rm","--network","none","-v",f"{work}:/data","-w","/data","--entrypoint","3dfier",image,"/data/config.yml","--OBJ","/data/lifted.obj"]
    r={"pass":False,"source_manifest":m,"image":image,"command":args}
    try:
        with (out/"engine.log").open("w") as log:
            result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
        r["exit_code"]=result.returncode
        if result.returncode:raise RuntimeError((out/"engine.log").read_text(errors="replace")[-6000:])
        p=work/"lifted.obj";vertices=[];faces=0;material=None;groups={}
        for l in p.read_text().splitlines():
            if l.startswith("v "):vertices.append(list(map(float,l.split()[1:4])))
            elif l.startswith("usemtl "):material=l.split(maxsplit=1)[1].strip()
            elif l.startswith("f "):
                faces+=1
                groups.setdefault(material or "unknown",set()).update(int(x.split("/")[0])-1 for x in l.split()[1:])
        if not vertices or faces<2 or not all(math.isfinite(v) for xyz in vertices for v in xyz):raise ValueError("Invalid lifted mesh")
        bounds=[[min(v[i] for v in vertices) for i in range(3)],[max(v[i] for v in vertices) for i in range(3)]]
        r.update(vertices=len(vertices),faces=faces,bounds=bounds,sha256=sha(p),material_z_ranges={k:[min(vertices[i][2] for i in v),max(vertices[i][2] for i in v)] for k,v in groups.items() if v})
        # Separate semantic gates; a valid flat road cannot hide a failed wall reconstruction.
        shutil.copy2(p,out/"lifted.obj")
        if m["source_type"]=="synthetic":
            mats=r["material_z_ranges"];road=next((z for k,z in mats.items() if k.lower()=="road"),None);wall=next((z for k,z in mats.items() if k.lower()=="separation"),None)
            r["checks"]={"road_datum":bool(road and 99.8<=road[0]<=100.2 and 100.2<=road[1]<=100.6),"wall_top":bool(wall and 101.35<=wall[1]<=101.9 and road and wall[1]-road[1]>=.8)}
            if not all(r["checks"].values()):raise ValueError("Semantic lifting gate failed: "+json.dumps(r["checks"]))
        r["pass"]=True
    finally:
        shutil.rmtree(work,ignore_errors=True)
        (out/"report.json").write_text(json.dumps(r,indent=2)+"\n")
    print("3DFIER_RESULT",json.dumps(r))
def main():
    p=argparse.ArgumentParser();sp=p.add_subparsers(dest="mode",required=True);f=sp.add_parser("fixture");f.add_argument("output",type=Path);f=sp.add_parser("run");f.add_argument("input",type=Path);f.add_argument("output",type=Path);f.add_argument("--image",required=True);a=p.parse_args()
    if a.mode=="fixture":fixture(a.output)
    else:run(a.input,a.output,a.image)
if __name__=="__main__":main()
