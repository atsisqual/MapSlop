#!/usr/bin/env python3
"""Install approved derivatives together; no source terrain alteration."""
import argparse,json,shutil,sys
from pathlib import Path
from collections import Counter
import numpy as np
import shapely as sh
from shapely.geometry import Polygon
from shapely.ops import triangulate
from PIL import Image
from terrain_grid import to_world

ROOT=Path(__file__).resolve().parent
PAVED={"paved","asphalt","concrete","concrete:plates","concrete:lanes","paving_stones","sett","cobblestone","unhewn_cobblestone","bricks","stone"}
UNPAVED={"unpaved","dirt","earth","grass","ground","gravel","fine_gravel","sand","mud","compacted"}
def patch(p,old,new):
    s=p.read_text()
    if s.count(old)!=1:raise ValueError(f"Unexpected {p.name}: {old[:100]}")
    p.write_text(s.replace(old,new,1))
def width(v,default):
    try:
        n=float(str(v).removesuffix(" m"))
        return n if .6<=n<=6 else default
    except (ValueError,TypeError):return default
def sides(t):
    value=t.get("sidewalk")
    out={}
    for name in ("left","right"):
        v=t.get("sidewalk:"+name,t.get("sidewalk:both",value))
        if v in ("yes","both",name):
            out[name]=width(t.get("sidewalk:"+name+":width",t.get("sidewalk:both:width",t.get("sidewalk:width"))),1.5)
    return out
def paving(osm):
    sidewalks={};paths={};areas=[]
    for e in osm["elements"]:
        if e.get("type")!="way":continue
        t=e.get("tags",{});id=str(e["id"]);g=e.get("geometry",[])
        if t.get("highway"):
            s=sides(t)
            if s:sidewalks[id]=s
            if t["highway"] in ("footway","pedestrian","steps","cycleway","path") and t.get("area")!="yes" and t.get("surface") not in UNPAVED and (t["highway"]!="path" or t.get("surface") in PAVED):
                paths[id]=width(t.get("width"),2.5 if t["highway"]=="pedestrian" else 1.5)
        if len(g)<4 or g[0]!=g[-1] or t.get("surface") in UNPAVED or "building" in t or "building:part" in t:continue
        if not (t.get("area")=="yes" and t.get("highway") in ("pedestrian","footway") or t.get("surface") in PAVED and (t.get("area")=="yes" or t.get("amenity")=="parking" or t.get("landuse")=="plaza")):continue
        p=Polygon([to_world(v["lon"],v["lat"]) for v in g]).buffer(0)
        if p.is_empty or not p.is_valid:continue
        ts=list(sh.constrained_delaunay_triangles(p).geoms)
        if abs(sum(q.area for q in ts)-p.area)>.01:raise ValueError("Incomplete explicit paving polygon "+id)
        for q in ts:
            q=sh.orient_polygons(q,exterior_cw=False) if hasattr(sh,"orient_polygons") else q
            areas.append({"id":id,"ring":[v for pt in list(q.exterior.coords)[:-1] for v in pt]})
    return {"sidewalks":sidewalks,"paths":paths,"areas":areas}
def roof_colors(geo,tiles):
    m=json.loads((tiles/"manifest.json").read_text());cache={}
    for t in m["tiles"]:
        d=t["levels"]["near"];cache[(t["i"],t["j"])]=np.array(Image.open(tiles/d["path"]).convert("RGB"))
    x0,z0,*_=m["world_extent"];s=m["tile_m"];g=m["gutter_m"]
    result={}
    for b in geo["buildings"]:
        def ring(r):return list(zip(r[::2],r[1::2]))
        poly=Polygon(ring(b["ring"]),[ring(h) for h in b.get("holes",[])]).buffer(0)
        inner=poly.buffer(-.75);margin=.75
        if inner.is_empty:inner=poly.buffer(-.35);margin=.35
        if inner.is_empty:result[str(b["id"])]={"class":"unknown","samples":0};continue
        x,z,X,Z=inner.bounds
        xx,zz=np.meshgrid(np.arange(x+.125,X,.5),np.arange(z+.125,Z,.5))
        inside=sh.contains_xy(inner,xx,zz);rgb=[]
        for a,c in zip(xx[inside],zz[inside]):
            i,j=int(np.floor((a-x0)/s)),int(np.floor((c-z0)/s));im=cache.get((i,j))
            if im is None:continue
            u=int(np.floor((a-x0-i*s+g)/.25));v=int(np.floor((c-z0-j*s+g)/.25))
            if 0<=u<im.shape[1] and 0<=v<im.shape[0]:rgb.append(im[v,u])
        if len(rgb)<4:result[str(b["id"])]={"class":"unknown","samples":len(rgb)};continue
        a=np.array(rgb,dtype=float);r,G,B=a.T
        valid=(a.mean(axis=1)>35)&~((G>r*1.12)&(G>B*1.12))
        a=a[valid]
        if len(a)<4:result[str(b["id"])]={"class":"unknown","samples":len(a)};continue
        r,G,B=a.T;red=(r-G>12)&(r-B>18)&(r>1.12*G)
        frac=float(red.mean());median=np.median(a,axis=0)
        if frac>=.4:
            cls="terracotta";med=np.median(a[red],axis=0);color=0xb65d42 if med.mean()>125 else 0x934b38
        else:
            cls="gray";color=0x77787a if median.mean()<115 else 0xaaa9a5 if median.mean()<175 else 0xd1d0c9
        result[str(b["id"])]={"class":cls,"color":color,"samples":len(a),"inner_margin_m":margin,"median_rgb":median.round().astype(int).tolist(),"terracotta_fraction":frac}
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument("out",type=Path);p.add_argument("tiles",type=Path);p.add_argument("trees",type=Path);p.add_argument("osm",type=Path);p.add_argument("--baseline",action="store_true");a=p.parse_args()
    out=a.out;js=out/"js";osm=json.loads(a.osm.read_text())
    import subprocess
    subprocess.run([sys.executable,str(ROOT/"install-orthophoto-preview.py"),str(out),str(a.tiles)],check=True)
    trees=json.loads(a.trees.read_text())["trees"]
    if len(trees)!=5702:raise ValueError("Not reviewed vegetation")
    shutil.copy2(ROOT/"pedome-vegetation-preview.mjs",js/"pedome-vegetation-preview.mjs")
    (js/"pedome-trees.mjs").write_text("export const trees="+json.dumps(trees,separators=(",",":"),allow_nan=False)+";\n")
    shell=js/"pedome.js"
    patch(shell,"import { installPedomeUI } from './pedome-ui.js';","import { installPedomeUI } from './pedome-ui.js';\nimport { installVegetation } from './pedome-vegetation-preview.mjs';\nimport { trees } from './pedome-trees.mjs';")
    patch(shell,"const camera=cameras.camera;","const camera=cameras.camera;const vegetation=installVegetation(scene,trees);")
    patch(shell,"orthoPreview:{ortho,scene,renderer,","vegetationPreview:{vegetation,scene,renderer},orthoPreview:{ortho,scene,renderer,")
    s=shell.read_text();old="ortho.update(camera);renderer.render(scene,camera);"
    if s.count(old)!=2:raise ValueError("Expected both render paths")
    shell.write_text(s.replace(old,"ortho.update(camera);vegetation.update(camera);renderer.render(scene,camera);"))
    if a.baseline:return
    f=js/"nairobi-geodata.js";s=f.read_text();prefix="export const GEO = ";start=s.index(prefix)+len(prefix);geo,end=json.JSONDecoder().raw_decode(s[start:])
    pav=paving(osm);colors=roof_colors(geo,a.tiles)
    geo["explicitPaving"]=pav;geo["roofColors"]=colors
    f.write_text(s[:start]+json.dumps(geo,separators=(",",":"),ensure_ascii=False,allow_nan=False)+s[start+end:])
    road=js/"road-network.js"
    patch(road,"...lanes, rank: l.rank, ring: l.ring, vmax: l.vmax","...lanes, rank: l.rank, ring: l.ring, vmax: l.vmax, osmWay:l.raw.way")
    patch(road,"rank: r.rank, ring: r.ring, vmax: r.vmax","rank: r.rank, ring: r.ring, vmax: r.vmax, osmWay:r.osmWay, osmForward:from===r.from")
    patch(road,"half, rank, ring }) => ({","half, rank, ring, osmWay, osmForward, divided }) => ({")
    patch(road,"span, half, rank, ring\n","span, half, rank, ring, osmWay, osmForward, divided\n")
    street=js/"street-geometry.js"
    patch(street,"for (const side of [-1, 1]) {\n      // (a metre past","for (const side of [-1, 1]) {\n      const sourceSide=(side*(e.osmForward?1:-1))>0?'right':'left';\n      const width=GEO.explicitPaving.sidewalks[e.osmWay]?.[sourceSide];\n      if(!width||e.divided)continue;\n      // (a metre past")
    patch(street,"side * (e.half + SIDEWALK), 1","side * (e.half + width), .25")
    patch(street,"const w = Math.max(1.6, r.w || 2) / 2;","const width=GEO.explicitPaving.paths[r.id];if(!width)continue;const w=width/2;")
    patch(street,"paths.add(q);","paths.add(q,{osmWay:r.id});")
    patch(street,"return { carriageways, service, sidewalks, paths };","for(const a of GEO.explicitPaving.areas)for(const q of offRoad(a.ring))paths.add(q,{osmWay:a.id});\n  return { carriageways, service, sidewalks, paths };")
    # Explicit at-grade paving should retain photographic detail.
    streets=js/"streets.js"
    patch(streets,"mesh(soups.path, createSidewalkMaterial(1), 'footpaths')","mesh(soups.path, new THREE.MeshStandardMaterial({color:0x99958e,roughness:1,transparent:true,opacity:.22,depthWrite:false}), 'footpaths')")
    b=js/"pedome-buildings-detail.mjs"
    patch(b,"const windows=[],doors=[],rows=[];","const sampledMaterials=new Map();\n  const windows=[],doors=[],rows=[];")
    patch(b,"rm=roof[Math.floor(hash(String(b.id)+'r')*roof.length)];","rm=roof[Math.floor(hash(String(b.id)+'r')*roof.length)];\n    let roofColor=null;")
    patch(b,"const result=simpleRoof(b,base,top,rm,fm);","roofColor=GEO.roofColors[String(b.id)]||{class:'unknown',samples:0};\n      const col=roofColor.color??0x98948e;if(!sampledMaterials.has(col))sampledMaterials.set(col,mat(col));\n      const result=simpleRoof(b,base,top,sampledMaterials.get(col),fm);")
    patch(b,"rows.push({osm_id:b.id,policy,reason,","rows.push({osm_id:b.id,policy,reason,roof_color:roofColor,")
    report={"sidewalk_ways":len(pav["sidewalks"]),"footway_ways":len(pav["paths"]),"explicit_area_ways":len({a["id"] for a in pav["areas"]}),"roof_color_counts":dict(Counter(v["class"] for v in colors.values()))}
    (out/"combined-source-report.json").write_text(json.dumps(report,indent=2)+"\n")
    print("COMBINED_SOURCES",json.dumps(report))
if __name__=="__main__":main()
