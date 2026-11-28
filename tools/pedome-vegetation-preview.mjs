// Private LiDAR tree preview: deterministic COS context, not measured species.
import * as THREE from 'three/webgpu';
import { heightAt } from './terrain.js';
const profile=code=>code==='5.1.1.6'?'eucalyptus':code.startsWith('5.1.1.')?'broadleaf':code.startsWith('2.2.2.')?'orchard':code.startsWith('6.')?'scrub':code.startsWith('2.')?'agriculture':'settlement';
const styles={
 eucalyptus:{shape:[.67,.83],start:[.43,.36],colors:[0x587d48,0x668b59]},
 broadleaf:{shape:[1,.82],start:[.28,.34],colors:[0x47713a,0x638542]},
 orchard:{shape:[1,.85],start:[.24,.32],colors:[0x6c8d45,0x7b9b54]},
 scrub:{shape:[.9,1],start:[.17,.26],colors:[0x667d45,0x768b50]},
 agriculture:{shape:[.85,1],start:[.30,.38],colors:[0x688c4b,0x54773c]},
 settlement:{shape:[1,.76],start:[.32,.39],colors:[0x4e773e,0x729650]}
};
const limits=[100,250,750], hash=(x,z)=>((Math.imul(Math.round(x*100),73856093)^Math.imul(Math.round(z*100),19349663))>>>0);
const tris=g=>(g.index?.count||g.attributes.position.count)/3;
export function installVegetation(scene,trees){
 const group=new THREE.Group(); group.name='PrivateLiDARVegetation';scene.add(group);
 const records=new Map(), trunkMat=new THREE.MeshStandardMaterial({color:0x695344,roughness:1});
 for(const t of trees){
  if(![t.x,t.z,t.height_m,t.crown_radius_proxy_m].every(Number.isFinite)||t.height_m<2.5||t.height_m>45)throw Error('Invalid tree candidate');
  const type=profile(t.cos_code),h=hash(t.x,t.z),v=h%2,key=type+':'+v;
  if(!records.has(key))records.set(key,{type,v,trees:[],tiers:[]});
  records.get(key).trees.push({...t,y:heightAt(t.x,t.z),rotation:h/4294967296*Math.PI*2});
 }
 for(const rec of records.values()){
  const {type,v}=rec,style=styles[type];
  const material=new THREE.MeshStandardMaterial({color:style.colors[v],roughness:1,flatShading:true});
  for(let tier=0;tier<3;tier++){
   const trunk=new THREE.CylinderGeometry(.62,1,1,[7,5,3][tier],1);
   const crown=tier===0?new THREE.IcosahedronGeometry(1,v===0?1:2):new THREE.IcosahedronGeometry(1,tier===1?1:0);
   const meshes=[new THREE.InstancedMesh(trunk,trunkMat,rec.trees.length),new THREE.InstancedMesh(crown,material,rec.trees.length)];
   for(const mesh of meshes){mesh.count=0;mesh.frustumCulled=false;mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);group.add(mesh);}
   rec.tiers.push({meshes,triangles:tris(trunk)+tris(crown),count:0});
  }
 }
 const dummy=new THREE.Object3D();let lastX=Infinity,lastZ=Infinity,stats=null;
 function update(camera,force=false){
  const {x,z}=camera.position;
  if(!force&&Math.hypot(x-lastX,z-lastZ)<12)return stats;
  lastX=x;lastZ=z;const start=performance.now();let calls=0,triangles=0;const counts=[0,0,0];
  for(const rec of records.values()){
   for(const tier of rec.tiers)tier.count=0;
   const style=styles[rec.type],v=rec.v;
   for(const t of rec.trees){
    const d=Math.hypot(t.x-x,t.z-z),i=limits.findIndex(l=>d<=l);if(i<0)continue;
    const tier=rec.tiers[i],n=tier.count++,h=t.height_m,r=t.crown_radius_proxy_m,base=h*style.start[v], crownH=h-base;
    const radius=Math.max(.10,Math.min(.40,h*.025));
    dummy.rotation.set(0,t.rotation,0);dummy.position.set(t.x,t.y+base/2,t.z);dummy.scale.set(radius,base,radius);dummy.updateMatrix();tier.meshes[0].setMatrixAt(n,dummy.matrix);
    dummy.position.set(t.x,t.y+base+crownH/2,t.z);dummy.scale.set(r*style.shape[v],crownH/2,r);dummy.updateMatrix();tier.meshes[1].setMatrixAt(n,dummy.matrix);
   }
   for(let i=0;i<3;i++){
    const tier=rec.tiers[i];counts[i]+=tier.count;triangles+=tier.count*tier.triangles;
    for(const mesh of tier.meshes){mesh.count=tier.count;mesh.visible=tier.count>0;mesh.instanceMatrix.needsUpdate=true;if(mesh.visible)calls++;}
   }
  }
  stats={total:trees.length,visible:counts.reduce((a,b)=>a+b,0),lod_counts:counts,draw_calls:calls,triangles,update_ms:performance.now()-start,models:records.size,limits_m:limits};
  return stats;
 }
 return {group,update,get stats(){return stats;}};
}
