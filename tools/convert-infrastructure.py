#!/usr/bin/env python3
"""Run selected offline infrastructure converters and retain exact receipts.
Outputs are candidates only, never install directly over approved terrain/physics.
"""
import argparse,hashlib,json,math,os,shutil,struct,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
    return h.hexdigest()
def glb_info(p):
    with p.open("rb") as f:
        magic,version,size=struct.unpack("<4sII",f.read(12));n,typ=struct.unpack("<I4s",f.read(8))
        if magic!=b"glTF" or version!=2 or size!=p.stat().st_size or typ!=b"JSON" or n>40_000_000:raise ValueError("Bad GLB")
        j=json.loads(f.read(n))
    meshes=j.get("meshes",[]);prims=[q for m in meshes for q in m["primitives"]]
    if not prims or not j.get("scenes"):raise ValueError("Empty model")
    if any("uri" in x for x in j.get("images",[])+j.get("buffers",[])):raise ValueError("GLB has external resources")
    tris=0
    for q in prims:
        if q.get("mode",4)==4:
            count=j["accessors"][q.get("indices",q["attributes"]["POSITION"])]["count"];tris+=count//3
    if tris<1:raise ValueError("No triangle primitives")
    return {"meshes":len(meshes),"primitives":len(prims),"triangles":tris,"materials":len(j.get("materials",[])),"images":len(j.get("images",[])),"bytes":size,"sha256":sha(p)}
def run(mode,src,out,exe=None):
    src=src.resolve();out=out.resolve();out.mkdir(parents=True,exist_ok=False)
    r={"pass":False,"mode":mode,"input_sha256":sha(src),"input_name":src.name,"commands":[]}
    def save():(out/"conversion-report.json").write_text(json.dumps(r,indent=2)+"\n")
    def command(args):
        path=shutil.which(str(args[0])) or (str(Path(args[0]).resolve()) if Path(args[0]).is_file() else None)
        if not path:raise ValueError("Executable unavailable: "+str(args[0]))
        cmd=[path,*map(str,args[1:])];r["commands"].append({"args":cmd,"executable_sha256":sha(Path(path))})
        with (out/f"command-{len(r['commands'])}.log").open("w") as log:
            result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=1800,cwd=out)
        r["commands"][-1]["exit_code"]=result.returncode
        if result.returncode:
            print((out/f"command-{len(r['commands'])}.log").read_text(errors="replace")[-10000:]);raise RuntimeError("Converter failed")
    try:
        if mode=="sumo":
            net=out/"network.net.xml";xodr=out/"network.xodr"
            command([exe or "netconvert","--osm-files",src,"--output-file",net,"--lefthand","false"])
            command([exe or "netconvert","--sumo-net-file",net,"--opendrive-output",xodr])
            a=ET.parse(net).getroot();b=ET.parse(xodr).getroot()
            edges=[e for e in a.findall("edge") if not e.get("function")]
            lanes=[l for e in edges for l in e.findall("lane")]
            roads=b.findall("road")
            if not edges or not lanes or not roads:raise ValueError("Empty road network")
            if any(float(l.get("length",0))<=0 or float(l.get("speed",0))<=0 for l in lanes):raise ValueError("Invalid lane")
            r.update(sumo_edges=len(edges),sumo_lanes=len(lanes),opendrive_roads=len(roads),opendrive_junctions=len(b.findall("junction")),projection=a.find("location").attrib if a.find("location") is not None else None,files={p.name:sha(p) for p in (net,xodr)},limitations="Topology/width/turn connections inferred by SUMO. Not a surveyed geometry or physics replacement.")
        elif mode=="osm2world":
            if not exe:raise ValueError("Explicit installed osm2world.sh required")
            # 0.4.0 release CLI; keep release style relative paths via launcher.
            dest=out/"scene.glb";command([exe,"-i",src,"-o",dest]);r.update(glb=glb_info(dest),limitations="Generated geometry/style estimates; own CRS/terrain alignment not validated; style asset licenses require separate review")
        elif mode=="cityjson":
            doc=json.loads(src.read_text())
            if doc.get("appearance",{}).get("textures"):raise ValueError("Textured CityJSON must use OBJ workflow; cjio GLB loses texture")
            dest=out/"scene.glb";command([exe or "cjio",src,"export","glb",dest]);r.update(glb=glb_info(dest),object_ids=sorted(doc["CityObjects"]),source_crs=doc.get("metadata",{}).get("referenceSystem"),source_transform=doc.get("transform"),limitations="GLB conversion only; local axes/scale and independent controls must be validated before use")
        else:raise ValueError("Unknown mode")
        r["pass"]=True
    except Exception as e:r["error"]=str(e);raise
    finally:save()
    print("INFRA_CONVERSION",json.dumps(r))
def main():
    p=argparse.ArgumentParser();p.add_argument("mode",choices=["sumo","osm2world","cityjson"]);p.add_argument("input",type=Path);p.add_argument("output",type=Path);p.add_argument("--executable");p.add_argument("--input-sha256",required=True);a=p.parse_args()
    if sha(a.input)!=a.input_sha256:raise ValueError("Input hash mismatch")
    run(a.mode,a.input,a.output,a.executable)
if __name__=="__main__":main()
