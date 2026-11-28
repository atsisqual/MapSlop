#!/usr/bin/env python3
"""Convert existing Overpass JSON to OSM XML with real node IDs and explicit spatial scope.
Never fetch data. Whole-feature inclusion only: crossing features are reported, not silently clipped.
"""
import argparse,collections,hashlib,json,math,xml.etree.ElementTree as ET
from pathlib import Path

def convert(doc,bounds=None,mode="all"):
    nodes={};ways={};relations={};selected_nodes=set();stats=collections.Counter();inventory=collections.Counter();missing=[]
    def inside(p):
        return bounds is None or bounds[0]<=p["lon"]<=bounds[2] and bounds[1]<=p["lat"]<=bounds[3]
    def node(i,p,tags=None):
        lat,lon=float(p["lat"]),float(p["lon"])
        if not math.isfinite(lat) or not math.isfinite(lon) or not -90<=lat<=90 or not -180<=lon<=180:raise ValueError("Invalid coordinates")
        i=int(i);old=nodes.get(i)
        if old and max(abs(old["lat"]-lat),abs(old["lon"]-lon))>1e-7:raise ValueError("Conflicting node coordinates "+str(i))
        nodes[i]={"lat":lat,"lon":lon,"tags":{**(old or {}).get("tags",{}),**(tags or {})}}
    def inventory_tags(t):
        for k in ("barrier","power","highway","amenity","railway","man_made","traffic_sign","kerb","sidewalk","wall","surface","bridge"):
            if k in t:inventory[k+"="+t[k]]+=1
    for e in doc["elements"]:
        typ=e["type"];i=int(e["id"]);t=e.get("tags",{})
        if typ=="node":
            node(i,e,t)
            if inside(e) and (mode=="all" or "highway" in t):selected_nodes.add(i);inventory_tags(t)
        elif typ=="way":
            if len(e.get("nodes",[]))!=len(e.get("geometry",[])) or len(e.get("nodes",[]))<2:
                raise ValueError("Incomplete way geometry "+str(i))
            for ref,p in zip(e["nodes"],e["geometry"]):node(ref,p)
            if mode=="roads" and "highway" not in t:continue
            if not all(inside(p) for p in e["geometry"]):
                stats["ways_excluded_not_wholly_inside"]+=1;continue
            if i in ways:raise ValueError("Duplicate way "+str(i))
            ways[i]=e;selected_nodes.update(e["nodes"]);inventory_tags(t)
        elif typ=="relation":relations[i]=e
    # Only complete relations; never fabricate member node IDs from geometry.
    kept={}
    for i,e in relations.items():
        if mode=="roads" and e.get("tags",{}).get("type")!="restriction":continue
        unresolved=[(m["type"],m["ref"]) for m in e.get("members",[]) if m["type"]=="way" and m["ref"] not in ways or m["type"]=="node" and m["ref"] not in selected_nodes or m["type"] not in ("way","node")]
        if unresolved or not e.get("members"):
            missing.append({"id":i,"missing_members":unresolved});continue
        kept[i]=e
    root=ET.Element("osm",version="0.6",generator="MapSlop offline converter")
    if bounds is not None:
        ET.SubElement(root,"bounds",minlat=str(bounds[1]),minlon=str(bounds[0]),maxlat=str(bounds[3]),maxlon=str(bounds[2]))
    def tags(el,t):
        for k,v in sorted(t.items()):ET.SubElement(el,"tag",k=str(k),v=str(v))
    for i in sorted(selected_nodes):
        n=nodes[i];el=ET.SubElement(root,"node",id=str(i),lat=format(n["lat"],".7f"),lon=format(n["lon"],".7f"));tags(el,n["tags"])
    for i,e in sorted(ways.items()):
        el=ET.SubElement(root,"way",id=str(i))
        for ref in e["nodes"]:ET.SubElement(el,"nd",ref=str(ref))
        tags(el,e.get("tags",{}))
    for i,e in sorted(kept.items()):
        el=ET.SubElement(root,"relation",id=str(i))
        for m in e["members"]:ET.SubElement(el,"member",type=m["type"],ref=str(m["ref"]),role=m.get("role",""))
        tags(el,e.get("tags",{}))
    return root,{"pass":bool(ways),"mode":mode,"bounds_lon_lat":bounds,"nodes":len(selected_nodes),"ways":len(ways),"relations":len(kept),"excluded_relations":missing,**stats,"inventory":dict(sorted(inventory.items()))}
def main():
    p=argparse.ArgumentParser();p.add_argument("input",type=Path);p.add_argument("output",type=Path);p.add_argument("--bounds",nargs=4,type=float);p.add_argument("--mode",choices=["all","roads"],default="all");a=p.parse_args()
    if a.bounds and not (a.bounds[0]<a.bounds[2] and a.bounds[1]<a.bounds[3]):raise ValueError("Invalid bounds")
    root,r=convert(json.loads(a.input.read_text()),a.bounds,a.mode)
    if not r["pass"]:raise ValueError("Empty conversion")
    a.output.mkdir(parents=True,exist_ok=False);dest=a.output/"map.osm";ET.ElementTree(root).write(dest,encoding="utf-8",xml_declaration=True)
    r.update(source_sha256=hashlib.sha256(a.input.read_bytes()).hexdigest(),output_sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
    (a.output/"report.json").write_text(json.dumps(r,indent=2)+"\n");print("OSM_CONVERSION",json.dumps(r))
if __name__=="__main__":main()
