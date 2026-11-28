#!/usr/bin/env python3
"""Local DGT church mesh candidate: measured class-6 roof envelope, estimated walls, DGT roof image.
No network requests; no proprietary map data. Output is independent of the game collision mesh.
"""
import argparse, hashlib, importlib.util, io, json, math, struct
from collections import Counter
from pathlib import Path
import numpy as np
import shapely as sh
from shapely.geometry import Polygon, box
from scipy.spatial import cKDTree
from pyproj import Transformer
import laspy
from PIL import Image
from terrain_grid import ORIGIN,KX,KY,to_world
from terrain_binary import decode
from terrain_tin import TinSampler
from roof_plane_fit import axis_frame
from roof_ransac import fit_regions
from facade_details import facade
import yaml
ROOT=Path(__file__).resolve().parents[1]
CHURCH=149406360
TERRAIN_SHA="36019dfc27584d667555c794350107c29981da4f4ee15bac2c03078aba0d895b"
spec=importlib.util.spec_from_file_location("vegetation",ROOT/"tools/build-dgt-vegetation.py")
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def jsonout(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+"\n")
def footprint():
    osm=json.loads((ROOT/"data/pedome/pedome-osm.json").read_text())
    e=next(e for e in osm["elements"] if e["type"]=="way" and e["id"]==CHURCH)
    p=Polygon([to_world(q["lon"],q["lat"]) for q in e["geometry"]])
    if not p.is_valid or p.area<10:raise ValueError("Invalid church footprint")
    return p
def points_from_lidar(root,p,base):
    names=[f"LO-{t}-07-2025_v05.laz" for t in v.b.TILES]
    sources=v.b.verify(root,names,v.b.TAG)
    tr=Transformer.from_crs(3763,4326,always_xy=True)
    inv=Transformer.from_crs(4326,3763,always_xy=True)
    x0,z0,x1,z1=p.bounds
    corners=[inv.transform(ORIGIN[1]+x/KX,ORIGIN[0]-z/KY) for x in (x0-2,x1+2) for z in (z0-2,z1+2)]
    emin,nmin=np.min(corners,axis=0)-1;emax,nmax=np.max(corners,axis=0)+1
    parts=[]
    for name in names:
        with laspy.open(root/name) as r:
            crs=r.header.parse_crs()
            h=next((c for c in crs.sub_crs_list if c.is_projected),crs) if crs is not None else None
            if h is None or h.to_epsg()!=3763:raise ValueError("Unexpected LAZ CRS")
            for chunk in r.chunk_iterator(1_000_000):
                e,n=np.asarray(chunk.x),np.asarray(chunk.y)
                hit=(np.asarray(chunk.classification)==6)&(e>=emin)&(e<=emax)&(n>=nmin)&(n<=nmax)
                if not hit.any():continue
                lon,lat=tr.transform(e[hit],n[hit]);x,z=to_world(lon,lat);y=np.asarray(chunk.z)[hit]-base
                keep=sh.intersects_xy(p,x,z)&np.isfinite(y)
                if keep.any():parts.append(np.column_stack((x[keep],y[keep],z[keep])))
    if not parts:raise ValueError("No class-6 returns within church footprint")
    return np.concatenate(parts),sources
def roof_samples(points,ground,cell=.5):
    # Retain highest return per occupied XY cell; lower wall returns are not roof evidence.
    keep=np.array([2<=y-ground(float(x),float(z))<=60 for x,y,z in points])
    points=points[keep]
    if len(points)<100:raise ValueError("Insufficient plausible roof returns")
    ix=np.floor(points[:,0]/cell).astype(int);iz=np.floor(points[:,2]/cell).astype(int)
    order=np.lexsort((-points[:,1],iz,ix));q=points[order];keys=np.column_stack((ix,iz))[order]
    q=q[np.r_[True,np.any(keys[1:]!=keys[:-1],axis=1)]]
    if len(q)<50:raise ValueError("Insufficient independent occupied cells")
    return q
def interpolator(samples):
    tree=cKDTree(samples[:,[0,2]])
    def sample(x,z):
        d,i=tree.query([x,z],k=3)
        w=1/np.maximum(d,.05)**2
        return float(np.dot(w,samples[i,1])/w.sum()),float(d[0])
    return sample
def roof_texture(runtime,p):
    m=json.loads((runtime/"ortho/manifest.json").read_text())
    x0,z0,x1,z1=p.bounds
    origin_x,origin_z=m["world_extent"][:2];s=m["tile_m"];g=m["gutter_m"];res=.25
    # Crop on the original shared world grid, with a one-pixel buffer.
    c0=math.floor((x0-origin_x)/res)-1;r0=math.floor((z0-origin_z)/res)-1
    c1=math.ceil((x1-origin_x)/res)+1;r1=math.ceil((z1-origin_z)/res)+1
    n=round(s/res);pad=round(g/res)
    img=Image.new("RGB",(c1-c0,r1-r0));coverage=np.zeros((r1-r0,c1-c0),bool);sources=[]
    for tile in m["tiles"]:
        i,j=tile["i"],tile["j"];a,b=i*n,j*n
        l,t,r,bot=max(c0,a),max(r0,b),min(c1,a+n),min(r1,b+n)
        if r<=l or bot<=t:continue
        d=tile["levels"]["near"];path=runtime/"ortho"/d["path"]
        if sha(path)!=d["sha256"]:raise ValueError("Roof texture source hash mismatch")
        with Image.open(path) as im:
            img.paste(im.convert("RGB").crop((l-a+pad,t-b+pad,r-a+pad,bot-b+pad)),(l-c0,t-r0))
        coverage[t-r0:bot-r0,l-c0:r-c0]=True;sources.append(d["sha256"])
    if not coverage.all():raise ValueError("Ortho crop not covered")
    buf=io.BytesIO();img.save(buf,format="PNG")
    return buf.getvalue(),[origin_x+c0*res,origin_z+r0*res,origin_x+c1*res,origin_z+r1*res],sources
def mesh(p,sample,ground,cell=.5):
    roofs=[];walls=[];support=[];edges={};area=0.
    x0,z0,x1,z1=p.bounds
    # Tessellate each clipped grid square with a constrained triangulation.
    for i in range(math.floor(x0/cell),math.ceil(x1/cell)):
        for j in range(math.floor(z0/cell),math.ceil(z1/cell)):
            clip=p.intersection(box(i*cell,j*cell,(i+1)*cell,(j+1)*cell))
            if clip.area<1e-9:continue
            for poly in sh.get_parts(clip):
                if poly.geom_type!="Polygon":continue
                for tri in sh.get_parts(sh.constrained_delaunay_triangles(poly)):
                    if tri.area<1e-10:continue
                    coords=[(round(x,7),round(z,7)) for x,z in list(tri.exterior.coords)[:3]]
                    if len(set(coords))!=3:continue
                    # Negative area in X/Z => upward normal in Y-up.
                    a,b,c=coords
                    if (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])>0:coords.reverse()
                    xyz=[]
                    for x,z in coords:
                        y,d=sample(x,z);support.append(d)
                        if y-ground(x,z)<1:raise ValueError("Roof intersects terrain")
                        xyz.append((x,y,z))
                    roofs.append(xyz);area+=tri.area
                    for k in range(3):
                        a,b=coords[k],coords[(k+1)%3];key=tuple(sorted((a,b)))
                        if key in edges:edges[key][2]+=1
                        else:edges[key]=[a,b,1]
    if abs(area-p.area)>max(.01,p.area*1e-5):raise ValueError("Roof footprint coverage mismatch")
    border=0.
    for a,b,n in edges.values():
        if n!=1:
            if n!=2:raise ValueError("Nonmanifold roof edge")
            continue
        from shapely.geometry import LineString
        segment=LineString([a,b])
        if segment.difference(p.boundary.buffer(1e-5)).length>1e-5:raise ValueError("Internal roof crack")
        border+=segment.length
        x,z=a;u,w=b
        at=(x,sample(x,z)[0],z);bt=(u,sample(u,w)[0],w)
        ab=(x,ground(x,z)-.02,z);bb=(u,ground(u,w)-.02,w)
        walls.extend([[ab,bb,bt],[ab,bt,at]])
    if abs(border-p.length)>.01:raise ValueError("Wall perimeter mismatch")
    return roofs,walls,np.array(support),area
def glb(path,roofs,walls,texture,uv_extent,details=None,config=None,pbr=None):
    details=details or {};config=config or {}
    # Standard self-contained glTF 2.0 binary. No external URLs or custom decoders.
    payload=bytearray();views=[];accessors=[]
    def view(data,target=None):
        while len(payload)%4:payload.append(0)
        index=len(views);views.append({"buffer":0,"byteOffset":len(payload),"byteLength":len(data)})
        if target:views[-1]["target"]=target
        payload.extend(data);return index
    def attrib(values,kind):
        a=np.asarray(values,dtype="<f4");i=len(accessors)
        d={"bufferView":view(a.tobytes(),34962),"componentType":5126,"count":len(a),"type":kind}
        if kind=="VEC3":d.update(min=a.min(axis=0).tolist(),max=a.max(axis=0).tolist())
        accessors.append(d);return i
    primitives=[]
    pbr=pbr or {}
    material_roles={1:'plaster',2:'granite'}
    for k,faces in enumerate((roofs,walls,details.get("granite",[]),details.get("door",[]),details.get("window",[]))):
        if not faces:continue
        a=np.asarray(faces,dtype=np.float64);normal=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]);length=np.linalg.norm(normal,axis=1)
        valid=length>1e-10;a=a[valid];normal=normal[valid]/length[valid,None]
        xyz=a.reshape(-1,3);attrs={"POSITION":attrib(xyz,"VEC3"),"NORMAL":attrib(np.repeat(normal,3,axis=0),"VEC3")}
        if k==0 and texture:
            x0,z0,x1,z1=uv_extent
            attrs["TEXCOORD_0"]=attrib(np.column_stack(((xyz[:,0]-x0)/(x1-x0),(xyz[:,2]-z0)/(z1-z0))),"VEC2")
        elif k in material_roles and material_roles[k] in pbr:
            role=material_roles[k];period=pbr[role]["period_m"]
            # Meter-based planar UV, continuous on coplanar wall strips; no roof/position changes.
            tangent=np.column_stack((normal[:,2],np.zeros(len(normal)),-normal[:,0]))
            tangent/=np.maximum(np.linalg.norm(tangent,axis=1)[:,None],1e-12)
            u=np.sum(a*tangent[:,None,:],axis=2).reshape(-1)/period
            v=-xyz[:,1]/period
            attrs["TEXCOORD_0"]=attrib(np.column_stack((u,v)),"VEC2")
        primitives.append({"attributes":attrs,"material":k,"mode":4})
    materials=[{"name":"Measured roof with aerial colour","doubleSided":True,"pbrMetallicRoughness":{"baseColorFactor":[.65,.24,.12,1],"metallicFactor":0,"roughnessFactor":.9}},{"name":"Estimated facade — NOT photographic","doubleSided":True,"pbrMetallicRoughness":{"baseColorFactor":[.75,.72,.65,1],"metallicFactor":0,"roughnessFactor":1}}]
    materials[1]['pbrMetallicRoughness']['baseColorFactor']=[*config.get('cor_parede_rgb',[.75,.72,.65]),1]
    for name,color in [('Granite quoins and surrounds',config.get('cor_granito_rgb',[.47,.45,.42])),('Estimated timber door',[.16,.085,.04]),('Estimated dark windows',[.075,.10,.12])]:
        materials.append({'name':name,'doubleSided':True,'pbrMetallicRoughness':{'baseColorFactor':[*color,1],'metallicFactor':0,'roughnessFactor':.9}})
    doc={"asset":{"version":"2.0","generator":"MapSlop local DGT church candidate"},"scene":0,"scenes":[{"nodes":[0]}],"nodes":[{"mesh":0}],"meshes":[{"primitives":primitives}],"materials":materials}
    if texture:
        doc.update(images=[{"bufferView":view(texture),"mimeType":"image/png"}],textures=[{"source":0,"sampler":0}],samplers=[{"magFilter":9729,"minFilter":9987,"wrapS":33071,"wrapT":33071}])
        materials[0]["pbrMetallicRoughness"].update(baseColorFactor=[1,1,1,1],baseColorTexture={"index":0})
    if pbr:
        images=doc.setdefault("images",[]);textures=doc.setdefault("textures",[]);samplers=doc.setdefault("samplers",[])
        repeat=len(samplers);samplers.append({"magFilter":9729,"minFilter":9987,"wrapS":10497,"wrapT":10497})
        def tex(blob,mime):
            i=len(images);images.append({"bufferView":view(blob),"mimeType":mime})
            j=len(textures);textures.append({"source":i,"sampler":repeat});return {"index":j}
        for k,role in material_roles.items():
            if role not in pbr:continue
            item=pbr[role];mat=materials[k];mr=mat["pbrMetallicRoughness"]
            mr.update(baseColorFactor=[1,1,1,1],baseColorTexture=tex(item["base"],"image/jpeg"),metallicFactor=0,roughnessFactor=1,metallicRoughnessTexture=tex(item["rough"],"image/png"))
            mat["normalTexture"]={**tex(item["normal"],"image/jpeg"),"scale":.65 if role=="granite" else .4}
    while len(payload)%4:payload.append(0)
    doc.update(buffers=[{"byteLength":len(payload)}],bufferViews=views,accessors=accessors)
    header=json.dumps(doc,separators=(",",":"),allow_nan=False).encode();header+=b" "*((-len(header))%4)
    data=struct.pack("<4sII",b"glTF",2,12+8+len(header)+8+len(payload))+struct.pack("<I4s",len(header),b"JSON")+header+struct.pack("<I4s",len(payload),b"BIN\0")+payload
    path.write_bytes(data)
def load_pbr(root):
    manifest=json.loads((root/"manifest.json").read_text())
    if manifest["provider"]!="Poly Haven" or manifest["license"]!="CC0-1.0":raise ValueError("Unapproved material source")
    data={}
    for role,asset in (("granite","granite_wall"),("plaster","white_plaster_rough_01")):
        rec=manifest["assets"][role]
        if rec["asset"]!=asset:raise ValueError("Unexpected asset")
        period=2.0 if role=="granite" else 3.0
        item={"period_m":period}
        for key in ("base","normal","rough"):
            m=rec["maps"][key];p=root/m["file"]
            if p.parent.resolve()!=root.resolve() or sha(p)!=m["sha256"]:raise ValueError("Material hash mismatch")
            raw=p.read_bytes();im=Image.open(io.BytesIO(raw));im.load()
            if list(im.size)!=m["size_px"]:raise ValueError("Material dimensions do not match lock")
            if key=="rough":
                g=im.convert("L");packed=Image.merge("RGB",(Image.new("L",g.size,255),g,Image.new("L",g.size,0)))
                buf=io.BytesIO();packed.save(buf,format="PNG");raw=buf.getvalue()
            item[key]=raw
        data[role]=item
    return data,manifest
def synthetic_pbr():
    result={}
    for role,c in (("granite",(135,128,115)),("plaster",(210,207,195))):
        item={"period_m":2.0}
        for name,color,fmt in (("base",c,"JPEG"),("normal",(128,128,255),"JPEG"),("rough",(255,200,0),"PNG")):
            buf=io.BytesIO();Image.new("RGB",(32,32),color).save(buf,format=fmt);item[name]=buf.getvalue()
        result[role]=item
    return result
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--fixture",action="store_true");ap.add_argument("--input",type=Path);ap.add_argument("--runtime",type=Path);ap.add_argument("--output",type=Path,required=True);ap.add_argument("--materials",type=Path);ap.add_argument("--approved-v1",type=Path);a=ap.parse_args()
    p=footprint();a.output.mkdir(parents=True,exist_ok=False);texture=None;uv=None;tex_sources=[];sources=[];rmse=None
    entry=next(b for b in yaml.safe_load((ROOT/'data/pedome/references/buildings.yaml').read_text())['buildings'] if int(b['osm_id'])==CHURCH)
    config=entry.get('detalhes_fachada') or {}
    if a.fixture:
        ground=lambda x,z:0.
        basis=axis_frame(p);corners=np.asarray(p.exterior.coords)@basis;u0,v0=corners.min(0);u1,v1=corners.max(0)
        pts=np.array([(x,z) for x in np.arange(p.bounds[0],p.bounds[2],.5) for z in np.arange(p.bounds[1],p.bounds[3],.5) if sh.intersects_xy(p,x,z)])
        uvlocal=pts@basis;u,vv=uvlocal.T;heights=10.-.30*np.abs(vv-(v0+v1)/2)
        tower=u>u1-5.5;heights[tower]=19.-.4*np.abs(vv[tower]-(v0+v1)/2)
        samples=np.column_stack((pts[:,0],heights,pts[:,1]));n=len(samples)
        # Synthetic checker image tests embedded texture decoding without external imagery.
        image=Image.new("RGB",(64,64));pix=np.indices((64,64)).sum(axis=0)//8%2
        image=Image.fromarray(np.where(pix[...,None],np.array([165,70,40]),np.array([220,150,100])).astype(np.uint8))
        buf=io.BytesIO();image.save(buf,format="PNG");texture=buf.getvalue();uv=list(p.bounds)
    else:
        if not a.input or not a.runtime:ap.error("Real input and approved runtime required")
        binpath=a.runtime/"js/terrain.bin"
        if sha(binpath)!=TERRAIN_SHA:raise ValueError("Not approved TIN")
        terrain=decode(binpath.read_bytes());ground=TinSampler(terrain)
        points,sources=points_from_lidar(a.input,p,terrain["base"]);samples=roof_samples(points,ground);n=len(samples)
        # Deterministic independent occupied-cell holdout, diagnostics not independent survey accuracy.
        texture,uv,tex_sources=roof_texture(a.runtime,p)
    train=samples[np.arange(n)%5!=0];test=samples[np.arange(n)%5==0]
    def score(sample,points):
        return float(np.sqrt(np.mean([(sample(x,z)[0]-y)**2 for x,y,z in points])))
    old_train=interpolator(train);old=interpolator(samples)
    baseline_rmse=score(old_train,test)
    old_roofs,old_walls,old_dist,old_area=mesh(p,old,ground)
    old_top=float(np.asarray(old_roofs)[:,:,1].max())
    def surface_vertices(faces):
        a=np.asarray(faces,dtype=np.float64);normal=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0])
        return a[np.linalg.norm(normal,axis=1)>1e-10].astype("<f4").reshape(-1,3)
    if not a.fixture:
        if not a.approved_v1 or sha(a.approved_v1)!="26e9bce51daaf408408fe8e63de621c61aed0cc788c6cfcc13fcfd5a1ebe42b9":raise ValueError("Require exact approved V1 GLB")
        raw=a.approved_v1.read_bytes();njson=struct.unpack_from("<I",raw,12)[0];doc=json.loads(raw[20:20+njson]);blob=raw[28+njson:]
        for i,faces in enumerate((old_roofs,old_walls)):
            ac=doc["accessors"][doc["meshes"][0]["primitives"][i]["attributes"]["POSITION"]];v=doc["bufferViews"][ac["bufferView"]];off=v.get("byteOffset",0)+ac.get("byteOffset",0)
            expected=np.frombuffer(blob[off:off+ac["count"]*12],dtype="<f4").reshape(-1,3)
            actual=surface_vertices(faces)
            if actual.shape!=expected.shape or np.max(np.abs(actual-expected))>2e-5:raise ValueError("V1 surface reproduction drift")
        if n!=1912 or abs(baseline_rmse-.4317902658049366)>1e-5 or abs(old_top-20.881288115940958)>1e-5:raise ValueError("V1 evidence reproduction drift")
    roofs,walls,dist,area=old_roofs,old_walls,old_dist,old_area
    height=lambda x,z:old(x,z)[0]
    rmse=baseline_rmse;regions=[{"name":"roof","kind":"V1 measured interpolation, tower/coruchéu unchanged"}]
    selection={"selected":"V1","baseline_holdout_rmse_m":baseline_rmse,"baseline_top_m":old_top,"candidate":None}
    try:
        pred,hold_lock,train_regions=fit_regions(p,train,old_train)
        candidate_rmse=score(pred,test)
        protected_test=np.array([hold_lock(x,z) for x,y,z in test])
        tower_rmse=score(pred,test[protected_test]) if protected_test.any() else None
        old_tower_rmse=score(old_train,test[protected_test]) if protected_test.any() else None
        candidate,locked,candidate_regions=fit_regions(p,samples,old)
        cr,cw,cd,ca=mesh(p,candidate,ground)
        top=float(np.asarray(cr)[:,:,1].max())
        v0=surface_vertices(old_roofs);v1=surface_vertices(cr)
        mask=np.array([locked(x,z) for x,y,z in v0])
        same_protected=bool(mask.any() and v0.shape==v1.shape and np.array_equal(v0[mask],v1[mask]))
        checks={"improved_holdout":candidate_rmse<=baseline_rmse-.005,"preserve_top":abs(top-old_top)<=.02,"preserve_tower_vertices":same_protected,"tower_holdout":tower_rmse is not None and tower_rmse<=old_tower_rmse+1e-9,"support":float(np.percentile(cd,95))<=2 and float(cd.max())<=5,"coverage":abs(ca-p.area)<=.01}
        selection["candidate"]={"holdout_rmse_m":candidate_rmse,"top_m":top,"protected_vertices":int(mask.sum()),"tower_holdout_rmse_m":tower_rmse,"baseline_tower_holdout_rmse_m":old_tower_rmse,"checks":checks,"regions":candidate_regions}
        if all(checks.values()):
            roofs,walls,dist,area=cr,cw,cd,ca
            height=lambda x,z:candidate(x,z)[0]
            rmse=candidate_rmse;regions=candidate_regions;selection["selected"]="RANSAC"
        else:selection["fallback_reason"]="RANSAC did not pass all V1 non-regression gates"
    except (ValueError, np.linalg.LinAlgError) as exc:
        selection["fallback_reason"]=str(exc)
    selection["approved_v1_reproduced"]=not a.fixture
    details,facade_report=facade(p,ground,height,config)
    pbr,material_manifest=load_pbr(a.materials) if a.materials else ((synthetic_pbr(),{"source":"synthetic fixture only"}) if a.fixture else ({},None))
    out=a.output/"church.glb";glb(out,roofs,walls,texture,uv,details,config,pbr)
    # Compare exact geometry bytes and roof image against an untextured-facade baseline.
    baseline=a.output/"geometry-control.glb";glb(baseline,roofs,walls,texture,uv,details,config)
    def inspect_glb(path):
        raw=path.read_bytes();n=struct.unpack_from("<I",raw,12)[0];j=json.loads(raw[20:20+n]);b=raw[28+n:]
        def buf(i):
            v=j["bufferViews"][i];return b[v.get("byteOffset",0):v.get("byteOffset",0)+v["byteLength"]]
        geo=[]
        for prim in j["meshes"][0]["primitives"]:
            attrs=prim["attributes"];geo.append((prim["material"],*[buf(j["accessors"][attrs[k]]["bufferView"]) for k in ("POSITION","NORMAL")]))
        return j,geo,buf(j["images"][0]["bufferView"])
    j,geo,roof_bytes=inspect_glb(out);_,before,before_roof=inspect_glb(baseline)
    baseline.unlink()
    if geo!=before or roof_bytes!=before_roof:raise ValueError("PBR changed geometry or measured roof")
    if pbr:
        for k in (1,2):
            mat=j["materials"][k];assert "normalTexture" in mat and "metallicRoughnessTexture" in mat["pbrMetallicRoughness"]
            assert all("TEXCOORD_0" in q["attributes"] for q in j["meshes"][0]["primitives"] if q["material"]==k)
    
    all_faces=roofs+walls+[tri for faces in details.values() for tri in faces]
    coords=np.asarray(all_faces).reshape(-1,3);lo=coords.min(axis=0);hi=coords.max(axis=0);center=(lo+hi)/2;half=(hi-lo)/2
    x,y,z=center;hx,hy,hz=half
    # 3D Tiles local Cartesian Z-up: X east, Y north, Z up. GLB is native Y-up.
    tiles={"asset":{"version":"1.1"},"geometricError":0,"root":{"boundingVolume":{"box":[x,-z,y,hx,0,0,0,hz,0,0,0,hy]},"geometricError":0,"refine":"REPLACE","content":{"uri":"church.glb"}}}
    jsonout(a.output/"tileset.json",tiles)
    report={"fixture":a.fixture,"osm_id":CHURCH,"source":"SYNTHETIC — NOT REAL" if a.fixture else "DGT class-6 roof envelope + OSM footprint + DGT 2025 orthophoto; walls and facade details estimated","origin_lat_lon":list(ORIGIN),"frame":"X east, Y above approved DGT terrain base, Z south","bounds":[lo.tolist(),hi.tolist()],"roof_triangles":len(roofs),"wall_triangles":len(walls),"footprint_m2":area,"roof_sample_cells":n,"holdout_rmse_m":rmse,"nearest_sample_p95_m":float(np.percentile(dist,95)),"nearest_sample_max_m":float(dist.max()),"glb_sha256":sha(out),"glb_bytes":out.stat().st_size,"source_hashes":sources,"texture_tile_sha256":tex_sources,"visual_review_required":True}
    report.update(materials=material_manifest,pbr_geometry_unchanged=True,pbr_measured_roof_unchanged=True,roof_regions=regions,roof_method=selection["selected"],roof_selection=selection,facade=facade_report,facade_triangles=sum(len(v) for v in details.values()),facade_config=config,previous_real_rmse_m=.4317902658049366,previous_real_top_m=20.881288115940958)
    report["checks"]={"facet_coverage":abs(area-p.area)<=.01,"facade":(not (config.get("porta_principal") or {}).get("enabled",True) or facade_report["door"]==1) and (not (config.get("janelas") or {}).get("enabled",True) or facade_report["window"]>0) and (not (config.get("cunhais_granito") or {}).get("enabled",True) or facade_report["quoin_strips"]>0),"tower":selection["selected"]=="V1" or selection["candidate"]["checks"]["preserve_tower_vertices"],"sample_support":report["nearest_sample_p95_m"]<=2 and report["nearest_sample_max_m"]<=5,"holdout_rmse":rmse<=baseline_rmse+1e-9 and (a.fixture or rmse<=.4317902658049366+1e-5),"preserve_measured_top":abs(float(np.asarray(roofs)[:,:,1].max())-old_top)<=.02}
    report["pass"]=bool(all(report["checks"].values()))
    jsonout(a.output/"church-report.json",report);print("CHURCH_CANDIDATE",json.dumps(report))
    if not report["pass"]:raise SystemExit("Roof support/holdout gate failed; do not integrate")
if __name__=="__main__":main()
