import * as THREE from 'three/webgpu';
// First bounded visual candidate: use the renderer already used by the game.
// One camera-centred shadow map, no full-screen AO or CSM dependency yet.
export function installLighting(scene,renderer,sun,hemi,buildings,quality='low'){
 if(!['off','low','high'].includes(quality))throw new Error('Invalid lighting quality');
 const state={quality,updates:0,casters:0,receivers:0,shadow_size:0,extent_m:0,tree_caster_batches:0,tree_caster_instances:0,tree_shadow_triangles:0};
 if(quality==='off')return {update(){},report:()=>({...state})};
 const high=quality==='high',size=high?1024:512,extent=high?95:64,step=8;
 state.shadow_size=size;state.extent_m=extent;
 scene.background=new THREE.Color(0xb8d1e9);scene.fog=new THREE.FogExp2(0xb8d1e9,0.00165);
 hemi.color.set(0xe1efff);hemi.groundColor.set(0x77705b);hemi.intensity=1.45;
 sun.color.set(0xffe4ba);sun.intensity=2.65;
 renderer.shadowMap.enabled=true;
 renderer.shadowMap.type=THREE.PCFShadowMap;
 sun.castShadow=true;sun.shadow.mapSize.set(size,size);
 sun.shadow.camera.left=-extent;sun.shadow.camera.right=extent;
 sun.shadow.camera.top=extent;sun.shadow.camera.bottom=-extent;
 sun.shadow.camera.near=1;sun.shadow.camera.far=300;
 sun.shadow.camera.updateProjectionMatrix();
 sun.shadow.bias=-0.0007;sun.shadow.normalBias=.16;
 state.bias=sun.shadow.bias;state.normalBias=sun.shadow.normalBias;
 sun.shadow.autoUpdate=false;sun.shadow.needsUpdate=true;
 if(!sun.target.parent)scene.add(sun.target);
 // Cast building shadows and nearby instanced canopies only; no trunks or distant LOD shadows.
 buildings.traverse(o=>{if(o.isMesh&&!o.isInstancedMesh){o.castShadow=true;state.casters++;}});
 const vegetation=scene.getObjectByName('PrivateLiDARVegetation');
 const canopy=[];
 if(vegetation)vegetation.children.forEach((o,i)=>{if(o.isInstancedMesh&&o.geometry.type==='IcosahedronGeometry'&&Math.floor(i/2)%3<(high?2:1)){o.castShadow=true;canopy.push(o);}});
 state.tree_caster_batches=canopy.length;
 scene.traverse(o=>{if(o.isMesh){o.receiveShadow=true;state.receivers++;}});
 let last=null;
 function update(camera){
  const p=camera.position;
  const x=Math.round(p.x/step)*step,y=Math.round(p.y/step)*step,z=Math.round(p.z/step)*step;
  state.tree_caster_instances=canopy.reduce((n,o)=>n+(o.visible?o.count:0),0);
  state.tree_shadow_triangles=canopy.reduce((n,o)=>n+(o.visible?o.count*(o.geometry.index?.count??o.geometry.attributes.position.count)/3:0),0);
  const key=x+','+y+','+z+';'+canopy.map(o=>o.instanceMatrix.version).join(',');
  if(key===last)return;
  last=key;sun.target.position.set(x,y,z);sun.position.set(x-105,y+140,z+90);
  sun.target.updateMatrixWorld(true);sun.updateMatrixWorld(true);
  sun.shadow.needsUpdate=true;state.updates++;
 }
 return {update,report:()=>({...state,shadow_enabled:renderer.shadowMap.enabled,sun_cast_shadow:sun.castShadow,fog:scene.fog.isFogExp2===true})};
}
