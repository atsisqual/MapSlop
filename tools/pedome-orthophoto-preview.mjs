import * as THREE from 'three/webgpu';
import {partitionTin} from './orthophoto-partition.mjs';
const levels=['far','mid','near'];
const maxActive={near:8,mid:20};
export async function installOrthophoto(scene,ground,renderer){
 const root=new URL('../ortho/',import.meta.url),res=await fetch(new URL('manifest.json',root));
 if(!res.ok)throw Error('Missing orthophoto manifest');
 const manifest=await res.json();
 if(manifest.schema!==1||manifest.tiles.length!==manifest.cols*manifest.rows)throw Error('Invalid orthophoto manifest');
 const geom=ground.geometry;
 const partition=partitionTin(geom.attributes.position.array,geom.attributes.normal.array,geom.index.array,manifest);
 const group=new THREE.Group();group.name='PrivateOrthophotoGround';group.visible=false;scene.add(group);
 const loader=new THREE.TextureLoader(),records=[],errors=[],stats={bytes_requested:0,loads:0,errors,partition:{area_original:partition.inputArea,area_render:partition.outputArea,triangles:partition.triangles,vertices:partition.parts.reduce((a,p)=>a+p.positions.length/3,0)}};
 async function load(r,l){
  const data=r.tile.levels[l];stats.bytes_requested+=data.bytes;stats.loads++;
  const tex=await loader.loadAsync(new URL(data.path,root).href);
  tex.name=data.path;tex.userData={level:l,metres_per_pixel:data.metres_per_pixel,expected_px:data.px};
  if(tex.image.width!==data.px||tex.image.height!==data.px){tex.dispose();throw Error('Unexpected tile dimensions '+data.path);}
  tex.colorSpace=THREE.SRGBColorSpace;tex.anisotropy=Math.min(8,renderer.getMaxAnisotropy?.()||4);
  return tex;
 }
 for(const tile of manifest.tiles){
  const p=partition.parts[tile.j*manifest.cols+tile.i];if(!p.indices.length)continue;
  const g=new THREE.BufferGeometry();
  g.setAttribute('position',new THREE.Float32BufferAttribute(p.positions,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(p.normals,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(p.uv,2));g.setIndex(p.indices);
  const m=new THREE.MeshStandardMaterial({roughness:.95});
  const mesh=new THREE.Mesh(g,m);mesh.name='Ortho-'+tile.i+'-'+tile.j;group.add(mesh);
  records.push({tile,mesh,base:null,current:null,level:'far',want:'far',pending:false,d:Infinity});
 }
 let cursor=0;
 async function init(){
  while(cursor<records.length){
   const r=records[cursor++];
   try{r.base=r.current=await load(r,'far');r.mesh.material.map=r.base;r.mesh.material.needsUpdate=true;}
   catch(e){errors.push(String(e));}
  }
 }
 await Promise.all(Array.from({length:6},init));
 if(errors.length)throw Error('Orthophoto base tiles failed: '+errors[0]);
 ground.visible=false;group.visible=true;
 let lastX=Infinity,lastZ=Infinity,inflight=0;
 function swap(r,texture,level){
  const old=r.current;r.current=texture;r.level=level;r.mesh.material.map=texture;r.mesh.material.needsUpdate=true;
  if(old&&old!==r.base&&old!==texture)old.dispose();
 }
 function pump(){
  for(const r of records.slice().sort((a,b)=>a.d-b.d)){
   if(inflight>=4)break;
   if(r.pending||r.level===r.want||r.want==='far')continue;
   const l=r.want;r.pending=true;inflight++;
   load(r,l).then(t=>{if(r.want===l)swap(r,t,l);else t.dispose();}).catch(e=>{errors.push(String(e));r.want=r.level;}).finally(()=>{inflight--;r.pending=false;pump();});
  }
 }
 function update(camera,force=false){
  const {x,z}=camera.position;
  if(!force&&Math.hypot(x-lastX,z-lastZ)<16)return;
  lastX=x;lastZ=z;
  for(const r of records){
   const [a,b,c,d]=r.tile.bounds;r.d=Math.hypot(Math.max(a-x,0,x-c),Math.max(b-z,0,z-d));r.want='far';
  }
  const order=records.slice().sort((a,b)=>a.d-b.d||a.tile.j-b.tile.j||a.tile.i-b.tile.i);
  let near=0,mid=0;
  for(const r of order){
   if(r.d<=180&&near<maxActive.near){r.want='near';near++;}
   else if(r.d<=360&&mid<maxActive.mid){r.want='mid';mid++;}
  }
  for(const r of records)if(r.want==='far'&&r.level!=='far')swap(r,r.base,'far');
  // Demote immediately to base when a nearer tile needs the budget; no accumulation.
  for(const r of records)if(levels.indexOf(r.level)>levels.indexOf(r.want))swap(r,r.base,'far');
  pump();
 }
 function inspect(x,z){
  const r=records.find(r=>{const [a,b,c,d]=r.tile.bounds;return x>=a&&x<c&&z>=b&&z<d;});
  if(!r)return null;
  const map=r.mesh.material.map,expected=r.tile.levels[r.level];
  const ray=new THREE.Raycaster(new THREE.Vector3(x,10000,z),new THREE.Vector3(0,-1,0));
  r.mesh.updateMatrixWorld(true);const hit=ray.intersectObject(r.mesh,false)[0];
  const uv=hit?.uv?.toArray()||null;
  const [a,b]=r.tile.bounds,span=manifest.tile_m+2*manifest.gutter_m,g=manifest.gutter_m;
  const world=uv?[a-g+uv[0]*span,b-g+(1-uv[1])*span]:null;
  const pixel=uv?[Math.min(expected.px-1,Math.max(0,Math.floor(uv[0]*expected.px))),Math.min(expected.px-1,Math.max(0,Math.floor((1-uv[1])*expected.px)))]:null;
  const pixelWorld=pixel?[a-g+(pixel[0]+.5)*span/expected.px,b-g+(pixel[1]+.5)*span/expected.px]:null;
  return {tile:r.tile.bounds,level:r.level,want:r.want,path:expected.path,texture_name:map?.name,texture_px:[map?.image?.width,map?.image?.height],metres_per_pixel:map?.userData?.metres_per_pixel,applied:map===r.current&&map?.name===expected.path&&map?.image?.width===expected.px&&map?.image?.height===expected.px&&r.mesh.visible&&group.visible&&!ground.visible,uv,world_from_mesh_uv:world,pixel,pixel_world:pixelWorld,alignment_error_m:world?Math.hypot(world[0]-x,world[1]-z):null,pixel_center_error_m:pixelWorld?Math.hypot(pixelWorld[0]-x,pixelWorld[1]-z):null};
 }
 function report(){
  const counts={far:0,mid:0,near:0};let textureBytes=0;
  for(const r of records){counts[r.level]++;textureBytes+=r.tile.levels.far.px**2*4*4/3;if(r.level!=='far')textureBytes+=r.tile.levels[r.level].px**2*4*4/3;}
  return {...stats,counts,estimated_texture_bytes:Math.ceil(textureBytes),inflight,settled:inflight===0&&records.every(r=>r.level===r.want),tile_count:records.length};
 }
 return {group,ground,manifest,update,report,inspect};
}
