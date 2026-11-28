#!/usr/bin/env python3
"""Offline, evidence-based cleanup of approved orthophoto. Never alter terrain or roof colour source."""
import argparse,copy,hashlib,importlib.util,json,math,shutil
from collections import Counter
from pathlib import Path
import numpy as np
import cv2
import laspy
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
from pyproj import Transformer
from scipy import ndimage as ndi
from PIL import Image
import shapely as sh
from shapely.geometry import Polygon,LineString
from terrain_grid import ORIGIN,KX,KY,to_world
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("vegetation",ROOT/"build-dgt-vegetation.py")
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def raster(polys,shape,x0,z0,cell):
    if not polys:return np.zeros(shape,bool)
    # Array row grows south (world z); rasterize in x/-z.
    from shapely.ops import transform
    return rasterize([(transform(lambda x,z,h=None:(x,-np.asarray(z)),p),1) for p in polys if not p.is_empty],out_shape=shape,transform=from_origin(x0,-z0,cell,cell),dtype="uint8").astype(bool)
def footprints(geo):
    def ring(r):return list(zip(r[::2],r[1::2]))
    return [Polygon(ring(b["ring"]),[ring(h) for h in b.get("holes",[])]).buffer(0) for b in geo["buildings"]]
def roads_and_parking(geo,osm):
    roads=[];parking=[]
    for r in geo["roads"]:
        if r.get("kind") in ("footway","pedestrian","steps","path","cycleway","track") or r.get("tunnel") or r.get("bridge"):continue
        pts=list(zip(r["pts"][::2],r["pts"][1::2]))
        if len(pts)>1:roads.append(LineString(pts).buffer(max(1.5,float(r.get("w",4))/2),cap_style=2))
    for e in osm["elements"]:
        t=e.get("tags",{});g=e.get("geometry",[])
        if t.get("amenity")=="parking" and t.get("parking")!="underground" and len(g)>=4 and g[0]==g[-1]:
            parking.append(Polygon([to_world(p["lon"],p["lat"]) for p in g]).buffer(0))
    return roads,parking
def lidar(root,x0,z0,shape,cell):
    names=[f"{kind}-{t}-07-2025_{ver}.{ext}" for t in v.b.TILES for kind,ver,ext in (("LO","v05","laz"),("MDT-50cm","v02","tif"))]
    sources=v.b.verify(root,names,v.b.TAG)
    ground,t=v.read_ground(root);g=np.asarray(ground.data);gm=np.ma.getmaskarray(ground)
    tr=Transformer.from_crs(3763,4326,always_xy=True);inv=Transformer.from_crs(4326,3763,always_xy=True)
    nz,nx=shape;xy=[inv.transform(ORIGIN[1]+x/KX,ORIGIN[0]-z/KY) for x in (x0,x0+nx*cell) for z in (z0,z0+nz*cell)]
    xmin,xmax=min(p[0] for p in xy)-3,max(p[0] for p in xy)+3;ymin,ymax=min(p[1] for p in xy)-3,max(p[1] for p in xy)+3
    counts=np.zeros((5,nx*nz),np.uint16);coverage=np.zeros(nx*nz,bool);classes=Counter()
    for tile in v.b.TILES:
        with laspy.open(root/f"LO-{tile}-07-2025_v05.laz") as reader:
            crs=reader.header.parse_crs();h=next((c for c in crs.sub_crs_list if c.is_projected),crs) if crs is not None else None
            if h is None or h.to_epsg()!=3763:raise ValueError("Unexpected LAZ CRS")
            for chunk in reader.chunk_iterator(1_000_000):
                ex,ny=np.asarray(chunk.x),np.asarray(chunk.y);hit=(ex>=xmin)&(ex<=xmax)&(ny>=ymin)&(ny<=ymax)
                if not hit.any():continue
                ex,ny,alt,cl=ex[hit],ny[hit],np.asarray(chunk.z)[hit],np.asarray(chunk.classification)[hit]
                lon,lat=tr.transform(ex,ny);xx,zz=to_world(lon,lat);c=np.floor((xx-x0)/cell).astype(int);r=np.floor((zz-z0)/cell).astype(int)
                keep=(c>=0)&(c<nx)&(r>=0)&(r<nz)
                ex,ny,alt,cl,c,r=(p[keep] for p in (ex,ny,alt,cl,c,r));idx=r*nx+c;coverage[idx]=True
                for k,n in zip(*np.unique(cl,return_counts=True)):classes[int(k)]+=int(n)
                rr=np.floor((ny-t.f)/t.e).astype(int);cc=np.floor((ex-t.c)/t.a).astype(int)
                good=(rr>=0)&(rr<g.shape[0])&(cc>=0)&(cc<g.shape[1])
                rr,cc,alt,cl,idx=(p[good] for p in (rr,cc,alt,cl,idx));dh=alt-g[rr,cc];valid=~gm[rr,cc]&np.isfinite(dh)
                for j,k in enumerate((3,4,5,6,1)):
                    ok=valid&(cl==k)&(dh>=(.65 if k==3 else .6 if k==1 else .8))&(dh<=(2.8 if k==1 else 60))
                    np.add.at(counts[j],idx[ok],1)
    return counts.reshape(5,nz,nx),coverage.reshape(shape),dict(classes),sources
def vehicle_candidates(count,allowed,excluded,cell):
    # Unclassified low elevated returns in compact road/parking clusters are only proxies.
    raw=(count>=2)&allowed&~excluded
    raw=ndi.binary_closing(raw,structure=np.ones((3,3),bool))&allowed&~excluded
    labels,n=ndi.label(raw,structure=np.ones((3,3),bool));out=np.zeros_like(raw);rows=[]
    for i,sl in enumerate(ndi.find_objects(labels),1):
        if sl is None:continue
        block=labels[sl]==i;area=block.sum()*cell*cell
        dims=sorted([(s.stop-s.start)*cell for s in sl])
        if 2<=area<=15 and 1<=dims[0]<=3 and 2<=dims[1]<=6 and dims[1]/dims[0]>=1.2:
            out[sl]|=block;rows.append({"row":sl[0].start,"col":sl[1].start,"area_m2":float(area),"dimensions_m":dims})
    return ndi.binary_dilation(out,iterations=1)&allowed&~excluded,rows
def white_objects(rgb,allowed,excluded,cell=.25):
    """Small bright elongated objects; proxy, not semantic car classifier."""
    lum=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY);bg=cv2.medianBlur(lum,21)
    raw=(lum>=175)&((rgb.max(2).astype(np.int16)-rgb.min(2))<=55)&(lum.astype(np.int16)-bg.astype(np.int16)>=25)&allowed&~excluded
    raw=ndi.binary_closing(raw,structure=np.ones((3,3),bool))&allowed&~excluded
    labels,n=ndi.label(raw,structure=np.ones((3,3),bool));out=np.zeros_like(raw);rows=[]
    for i,sl in enumerate(ndi.find_objects(labels),1):
        if sl is None:continue
        block=labels[sl]==i;area=block.sum()*cell*cell
        yy,xx=np.nonzero(block);pts=np.column_stack((xx,yy)).astype(np.float32)*cell
        if len(pts)<8:continue
        _,(w,h),_=cv2.minAreaRect(pts);short,long=sorted((w+cell,h+cell))
        if 1.2<=area<=13 and .85<=short<=3 and 1.8<=long<=5.8 and long/short>=1.25 and area/(short*long)>=.48:
            out[sl]|=block;rows.append({"row":sl[0].start,"col":sl[1].start,"area_m2":float(area),"dimensions_m":[float(short),float(long)]})
    return ndi.binary_dilation(out,iterations=2)&allowed&~excluded,rows

def bounded_components(mask,cell=.25,max_m2=24):
    labels,n=ndi.label(mask,structure=np.ones((3,3),bool));out=np.zeros_like(mask);rows=[]
    for i,sl in enumerate(ndi.find_objects(labels),1):
        if sl is None:continue
        b=labels[sl]==i;area=float(b.sum()*cell*cell);span=max(s.stop-s.start for s in sl)*cell
        if area<=max_m2 and span<=8:
            out[sl]|=b;rows.append({"row":sl[0].start,"col":sl[1].start,"area_m2":area,"span_m":span})
    return out,rows

def fill_rgb(rgb,mask,paved):
    out=rgb.copy()
    for region in (paved,~paved):
        target=mask&region
        labels,n=ndi.label(target,structure=np.ones((3,3),bool))
        for i,sl in enumerate(ndi.find_objects(labels),1):
            if sl is None:continue
            pad=16;ys,xs=sl;roi=np.s_[max(0,ys.start-pad):min(mask.shape[0],ys.stop+pad),max(0,xs.start-pad):min(mask.shape[1],xs.stop+pad)]
            m=mask[roi]|~region[roi];sel=labels[roi]==i
            if not (~m).any():raise ValueError("No same-surface donor")
            patch=cv2.inpaint(np.ascontiguousarray(rgb[roi]),np.ascontiguousarray(m.astype(np.uint8)*255),3,cv2.INPAINT_TELEA)
            out[roi][sel]=patch[sel]
    assert np.array_equal(out[~mask],rgb[~mask])
    return out,{"method":"OpenCV Telea radius 3 px","paved":{"pixels":int((mask&paved).sum())},"other":{"pixels":int((mask&~paved).sum())}}

def visual_metrics(before,after,mask):
    b=cv2.cvtColor(before,cv2.COLOR_RGB2GRAY).astype(np.float32);a=cv2.cvtColor(after,cv2.COLOR_RGB2GRAY).astype(np.float32)
    safe=~ndi.maximum_filter(mask,size=9)
    var=lambda x:np.maximum(0,cv2.boxFilter(x*x,-1,(9,9))-cv2.boxFilter(x,-1,(9,9))**2)
    vb,va=var(b),var(a);d=np.abs(va[safe]-vb[safe])
    return {"unmasked_rgb_mae":float(np.abs(before.astype(np.int16)-after.astype(np.int16))[~mask].mean()) if (~mask).any() else 0.,
            "local_variance_abs_p95":float(np.percentile(d,95)) if d.size else 0.,
            "local_variance_relative_change":float(d.sum()/max(1,vb[safe].sum())),
            "unmasked_exact":bool(np.array_equal(before[~mask],after[~mask]))}

def main():
    p=argparse.ArgumentParser();p.add_argument("--input",type=Path,required=True);p.add_argument("--runtime",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--evidence",type=Path,required=True);a=p.parse_args()
    src=a.runtime/"ortho";m=load(src/"manifest.json");new=copy.deepcopy(m)
    g=m["gutter_m"];s=m["tile_m"];n=int(s/.25);pad=int(g/.25);x0,z0=m["world_extent"][:2]
    cols,rows=m["cols"],m["rows"];shape=(rows*n+2*pad,cols*n+2*pad)
    rgb=np.zeros((*shape,3),np.uint8)
    for tile in m["tiles"]:
        d=tile["levels"]["near"];path=src/d["path"]
        if sha(path)!=d["sha256"]:raise ValueError("Source tile hash")
        im=np.asarray(Image.open(path).convert("RGB"));i,j=tile["i"],tile["j"]
        rgb[j*n:j*n+n+2*pad,i*n:i*n+n+2*pad]=im
    geo,_=json.JSONDecoder().raw_decode((a.runtime/"js/nairobi-geodata.js").read_text().split("export const GEO = ",1)[1])
    osm=load(ROOT.parent/"data/pedome/pedome-osm.json")
    rp,pp=roads_and_parking(geo,osm);coarse=(shape[0]//2,shape[1]//2);cx,cz=x0-g,z0-g
    counts,cov,classes,sources=lidar(a.input,cx,cz,coarse,.5)
    roofs=raster(footprints(geo),coarse,cx,cz,.5)
    road=raster(rp,coarse,cx,cz,.5);parking=raster(pp,coarse,cx,cz,.5)
    veg=ndi.binary_closing((counts[0]>=2)|(counts[1]>=1)|(counts[2]>=1),structure=np.ones((3,3),bool))
    veg=ndi.binary_dilation(veg,iterations=1)&~road&~roofs
    building=ndi.binary_dilation((counts[3]>=2)|roofs,iterations=1)&~road
    cars,candidates=vehicle_candidates(counts[4],road|parking,building|veg,.5)
    up=lambda x:np.repeat(np.repeat(x,2,axis=0),2,axis=1)
    cos=load(ROOT.parent/"data/pedome/cos2025-pilot.geojson")
    from shapely.geometry import shape as geomshape
    from shapely.ops import transform
    forest=[]
    for feature in cos["features"]:
        code=str(feature["properties"].get("cos25v1_n4_c",""))
        if code.startswith(("5","6")):
            forest.append(transform(lambda lon,lat,h=None:to_world(np.asarray(lon),np.asarray(lat)),geomshape(feature["geometry"])))
    forest_mask=raster(forest,coarse,cx,cz,.5)
    protected=up(veg|building|roofs|forest_mask)
    paved=up(road|parking)
    yy,xx=np.ogrid[:shape[0],:shape[1]]
    church_zone=((cx+(xx+.5)*.25)**2+(cz+(yy+.5)*.25)**2)<=60**2
    white,white_rows=white_objects(rgb,paved|church_zone,protected)
    mask,components=bounded_components((up(cars)|white)&~protected)
    filled,metrics=fill_rgb(rgb,mask,paved)
    a.output.mkdir(parents=True,exist_ok=False);a.evidence.mkdir(parents=True,exist_ok=True)
    totals={k:0 for k in ("far","mid","near")};changed=0;visual=[];protected_changed=0
    for tile in new["tiles"]:
        i,j=tile["i"],tile["j"];sl=np.s_[j*n:j*n+n+2*pad,i*n:i*n+n+2*pad];local=mask[sl]
        if local.any():changed+=1
        for level,d in tile["levels"].items():
            dest=a.output/d["path"];source=src/d["path"]
            if sha(source)!=d["sha256"]:raise ValueError("Source hash mismatch")
            old=np.asarray(Image.open(source).convert("RGB"));px=d["px"]
            if level=="near":
                lm=local;protection=protected[sl];replacement=filled[sl]
            else:
                lm=np.asarray(Image.fromarray(local.astype(np.uint8)*255).resize((px,px),Image.Resampling.BOX))>=128
                protection=np.asarray(Image.fromarray(protected[sl].astype(np.uint8)*255).resize((px,px),Image.Resampling.BOX))>0
                lm=lm&~protection
                replacement=np.asarray(Image.fromarray(filled[sl]).resize((px,px),Image.Resampling.BOX))
            if not lm.any():shutil.copy2(source,dest)
            else:
                patched=old.copy();patched[lm]=replacement[lm]
                Image.fromarray(patched).save(dest,"WEBP",lossless=True,method=4)
            actual=np.asarray(Image.open(dest).convert("RGB"))
            vm=visual_metrics(old,actual,lm);vm.update(tile=[i,j],level=level);visual.append(vm)
            protected_changed+=int(np.any(old!=actual,axis=2)[protection].sum())
            d["bytes"]=dest.stat().st_size;d["sha256"]=sha(dest);totals[level]+=d["bytes"]
            if d["bytes"]>1048576:raise ValueError("Tile exceeds revised 1 MiB safety ceiling")
    new["bytes_by_level"]=totals;new["cleanup"]={"source_manifest_sha256":sha(src/"manifest.json"),"method":"small bounded object proxies; OpenCV Telea; original protected pixels; lossless changed tiles"}
    (a.output/"manifest.json").write_text(json.dumps(new,indent=2)+"\n")
    preview=np.zeros_like(rgb);preview[protected]=[0,110,0];preview[mask]=[0,160,255]
    for name,img in (("mask",preview),("mosaic-before",rgb),("mosaic-after",filled)):
        Image.fromarray(img).resize((cols*256,rows*256)).save(a.evidence/(name+".png"))
    rr,cc=round(-cz/.25),round(-cx/.25);roi=np.s_[max(0,rr-240):rr+240,max(0,cc-240):cc+240]
    for name,img in (("church-objects-before",rgb),("church-objects-after",filled),("church-objects-mask",preview)):
        Image.fromarray(img[roi]).save(a.evidence/(name+".png"))
    # Coverage measured only over the approved terrain extent (not padded tile edges).
    _,_,x1,z1=m["world_extent"];valid=cov[int(g/.5):int(g/.5)+math.ceil((z1-z0)/.5),int(g/.5):int(g/.5)+math.ceil((x1-x0)/.5)]
    coverage=float(ndi.maximum_filter(valid,size=5).mean())
    report={"pass":False,"sources":sources,"class_counts":classes,"coverage_2_5m_proxy":coverage,"mask_m2":{"vegetation":0.,"building":0.,"vehicle_proxy":float(mask.sum()*.0625),"protected":float(protected.sum()*.0625)},"vehicle_candidates":candidates,"white_object_candidates":white_rows,"bounded_components":components,"church_mask_pixels":int((mask&church_zone).sum()),"fill":metrics,"tiles_changed":changed,"bytes_by_level":totals,"unmasked_exact_before_encoding":True,"protected_pixels_changed":protected_changed,"visual_metrics":visual,"unmasked_tile_mean_abs_rgb_max":max(v["unmasked_rgb_mae"] for v in visual),"road_nonvehicle_mask_pixels":0}
    report["pass"]=bool(coverage>=.95 and mask.any() and not (mask&protected).any() and changed>0 and protected_changed==0 and all(v["unmasked_exact"] and v["local_variance_abs_p95"]<=1e-3 and v["local_variance_relative_change"]<=1e-6 for v in visual) and totals["far"]<=1_000_000 and sum(totals.values())<=32_000_000)
    (a.evidence/"clean-mask-report.json").write_text(json.dumps(report,indent=2)+"\n")
    print("CLEAN_MASK",json.dumps({k:w for k,w in report.items() if k not in ("sources","vehicle_candidates","white_object_candidates","bounded_components","visual_metrics")}))
    if not report["pass"]:raise SystemExit("Cleanup gate failed")
if __name__=="__main__":main()
