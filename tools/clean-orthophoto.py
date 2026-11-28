#!/usr/bin/env python3
"""Offline, evidence-based cleanup of approved orthophoto. Never alter terrain or roof colour source."""
import argparse,copy,hashlib,importlib.util,json,math,shutil
from collections import Counter
from pathlib import Path
import numpy as np
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
def fill_rgb(rgb,mask,paved):
    # Only change masked pixels; source donors never come from another masked object.
    out=rgb.copy();metrics={}
    for name,region in (("paved",paved),("other",~paved)):
        target=mask&region;donors=~mask&region
        if not target.any():metrics[name]={"pixels":0};continue
        if not donors.any():raise ValueError("No unmasked donors for "+name)
        dist,idx=ndi.distance_transform_edt(~donors,return_indices=True)
        out[target]=rgb[idx[0][target],idx[1][target]]
        metrics[name]={"pixels":int(target.sum()),"donor_distance_p95_m":float(np.percentile(dist[target],95)*.25),"donor_distance_max_m":float(dist[target].max()*.25)}
        del dist,idx
    # Smooth only the filled pixels (not real unmasked photographic detail).
    for c in range(3):
        smooth=ndi.gaussian_filter(out[:,:,c].astype(np.float32),sigma=2)
        out[:,:,c][mask]=np.rint(smooth[mask]).clip(0,255).astype(np.uint8)
    if not np.array_equal(out[~mask],rgb[~mask]):raise ValueError("Unmasked source modified")
    return out,metrics
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
    mask=up(veg|building|cars);paved=up(road|parking)
    filled,metrics=fill_rgb(rgb,mask,paved)
    a.output.mkdir(parents=True,exist_ok=False);a.evidence.mkdir(parents=True,exist_ok=True)
    totals={k:0 for k in ("far","mid","near")};changed=0;unmasked_error=[]
    for tile in new["tiles"]:
        i,j=tile["i"],tile["j"];sl=np.s_[j*n:j*n+n+2*pad,i*n:i*n+n+2*pad];local=mask[sl];image=Image.fromarray(filled[sl])
        for level,d in tile["levels"].items():
            dest=a.output/d["path"]
            if not local.any():shutil.copy2(src/d["path"],dest)
            else:
                im=image if level=="near" else image.resize((d["px"],d["px"]),Image.Resampling.LANCZOS)
                im.save(dest,"WEBP",quality={"near":82,"mid":78,"far":75}[level],method=4)
            d["bytes"]=dest.stat().st_size;d["sha256"]=sha(dest);totals[level]+=d["bytes"]
            if d["bytes"]>262144:raise ValueError("Tile exceeds existing 256 KiB budget")
        if local.any():
            changed+=1
            old=np.asarray(Image.open(src/tile["levels"]["near"]["path"]).convert("RGB"),dtype=np.int16)
            actual=np.asarray(Image.open(a.output/tile["levels"]["near"]["path"]).convert("RGB"),dtype=np.int16)
            if (~local).any():unmasked_error.append(float(np.abs(actual-old)[~local].mean()))
    new["bytes_by_level"]=totals;new["cleanup"]={"source_manifest_sha256":sha(src/"manifest.json"),"method":"LiDAR 3–6, OSM footprints, conservative unclassified compact vehicle proxies; neighbouring same paved/nonpaved donors; synthetic ground, not recovered photo"}
    (a.output/"manifest.json").write_text(json.dumps(new,indent=2)+"\n")
    preview=np.zeros_like(rgb);preview[up(veg)]=[0,180,0];preview[up(building)]=[220,80,0];preview[up(cars)]=[0,160,255]
    for name,img in (("mask",preview),("mosaic-before",rgb),("mosaic-after",filled)):
        Image.fromarray(img).resize((cols*256,rows*256)).save(a.evidence/(name+".png"))
    # Coverage measured only over the approved terrain extent (not padded tile edges).
    _,_,x1,z1=m["world_extent"];valid=cov[int(g/.5):int(g/.5)+math.ceil((z1-z0)/.5),int(g/.5):int(g/.5)+math.ceil((x1-x0)/.5)]
    coverage=float(ndi.maximum_filter(valid,size=5).mean())
    report={"pass":False,"sources":sources,"class_counts":classes,"coverage_2_5m_proxy":coverage,"mask_m2":{"vegetation":float(veg.sum()*.25),"building":float(building.sum()*.25),"vehicle_proxy":float(cars.sum()*.25)},"vehicle_candidates":candidates,"fill":metrics,"tiles_changed":changed,"bytes_by_level":totals,"unmasked_exact_before_encoding":True,"unmasked_tile_mean_abs_rgb_max":max(unmasked_error,default=0),"road_nonvehicle_mask_pixels":int(((veg|building)&road).sum())}
    report["pass"]=coverage>=.95 and veg.any() and building.any() and changed>0 and totals["far"]<=1_000_000 and max(unmasked_error,default=0)<=8 and report["road_nonvehicle_mask_pixels"]==0
    (a.evidence/"clean-mask-report.json").write_text(json.dumps(report,indent=2)+"\n")
    print("CLEAN_MASK",json.dumps({k:w for k,w in report.items() if k not in ("sources","vehicle_candidates")}))
    if not report["pass"]:raise SystemExit("Cleanup gate failed")
if __name__=="__main__":main()
