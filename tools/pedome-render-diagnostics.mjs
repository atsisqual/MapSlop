import * as THREE from 'three/webgpu';

const generated=new WeakSet();
const queries=()=>new URLSearchParams(location.search);
export const isPOT=n=>Number.isInteger(n)&&n>0&&Number.isInteger(Math.log2(n));
export function rendererOptions(){
 const q=queries();
 return {antialias:true,forceWebGL:!navigator.gpu||q.has('webgl')||q.get('renderer')==='webgl'};
}
export function configureGroundTexture(tex,renderer){
 const max=Math.max(1,renderer.getMaxAnisotropy()||1);
 const mobile=/Android/i.test(navigator.userAgent);
 const requested=Number(queries().get('anisotropy')|| (mobile?1:8));
 tex.generateMipmaps=true;tex.mipmapsAutoUpdate=true;
 tex.minFilter=THREE.LinearMipmapLinearFilter;tex.magFilter=THREE.LinearFilter;
 tex.anisotropy=Math.min(max,Math.max(1,Number.isFinite(requested)?Math.floor(requested):1));
 tex.needsUpdate=true;
 return tex;
}
export function textureState(tex,renderer){
 const w=tex.image?.width,h=tex.image?.height;
 const b=renderer.backend, data=b.get(tex);
 const expected=isPOT(w)&&isPOT(h)?1+Math.log2(Math.max(w,h)):null;
 const levels=b.isWebGPUBackend?data.texture?.mipLevelCount??null:null;
 return {name:tex.name,width:w,height:h,pot:isPOT(w)&&isPOT(h),
  generateMipmaps:tex.generateMipmaps,autoUpdate:tex.mipmapsAutoUpdate,
  minFilter:tex.minFilter,magFilter:tex.magFilter,
  trilinear:tex.minFilter===THREE.LinearMipmapLinearFilter&&tex.magFilter===THREE.LinearFilter,
  anisotropy:tex.anisotropy,expectedLevels:expected,gpuLevels:levels,
  generated:generated.has(tex)};
}
export async function installRenderDiagnostics(renderer){
 const b=renderer.backend, original=b.generateMipmaps;
 if(typeof original!=='function')throw Error('Unknown mipmap backend');
 b.generateMipmaps=function(texture,...args){
  const result=original.call(this,texture,...args);
  generated.add(texture);return result;
 };
 const backend=b.isWebGPUBackend?'WebGPU':b.isWebGLBackend?'WebGL2':'unknown';
 let gpu={};
 if(b.isWebGPUBackend){
  const adapter=b.device?.adapterInfo?null:await navigator.gpu?.requestAdapter({featureLevel:'compatibility'}).catch(()=>null);
  const info=b.device?.adapterInfo||adapter?.info||await adapter?.requestAdapterInfo?.().catch(()=>null);
  gpu.infoSource=b.device?.adapterInfo?'device':adapter?'separate-adapter-query':'unavailable';
  if(info)for(const k of ['vendor','architecture','device','description','isFallbackAdapter'])if(info[k]!==undefined)gpu[k]=info[k];
 }else if(b.isWebGLBackend){
  const gl=b.gl,ext=gl.getExtension('WEBGL_debug_renderer_info');
  gpu={vendor:gl.getParameter(ext?ext.UNMASKED_VENDOR_WEBGL:gl.VENDOR),renderer:gl.getParameter(ext?ext.UNMASKED_RENDERER_WEBGL:gl.RENDERER),depthBits:gl.getParameter(gl.DEPTH_BITS),masked:!ext};
 }
 const errors=[];
 b.device?.addEventListener?.('uncapturederror',e=>errors.push(String(e.error?.message||e.error)));
 const q=queries(),debug=q.get('debug')==='1';
 if(debug){
  const panel=document.createElement('pre');panel.id='render-debug';
  Object.assign(panel.style,{position:'fixed',top:'52px',right:'6px',zIndex:'9',margin:'0',padding:'6px',background:'#111d',color:'white',font:'11px monospace',maxWidth:'80vw',maxHeight:'40vh',overflow:'auto',pointerEvents:'none',whiteSpace:'pre-wrap'});
  document.body.append(panel);
  const update=()=>{
   const s=window.mapslop?.renderDebug?.();
   if(s){const t=s.textures;panel.textContent=JSON.stringify({...s,textures:{count:t.length,generated:t.filter(x=>x.generated).length,invalid:t.filter(x=>!x.pot||!x.generateMipmaps||!x.trilinear).length,sample:t.find(x=>x.generated)||t[0]||null}},null,1);}
  };
  setInterval(update,1000);
 }
 return (scene,ortho,camera)=>{
  const textures=new Set();
  scene.traverse(o=>{if(o.name==='ground'||o.name.startsWith('Ortho-')||['asphalt','sidewalks','footpaths','kerbs'].includes(o.name))for(const m of (Array.isArray(o.material)?o.material:[o.material]))if(m?.map)textures.add(m.map);});
  return {backend,gpu,maxAnisotropy:renderer.getMaxAnisotropy(),orthoEnabled:ortho?.group?.visible??false,
   baseGroundVisible:ortho?.ground?.visible??scene.getObjectByName('ground')?.visible??null,
   shadows:renderer.shadowMap?.enabled??false,near:camera.near,far:camera.far,errors:[...errors],
   textures:[...textures].map(t=>textureState(t,renderer))};
 };
}
export function improveDepth(camera,scene){
 // This pilot is ~1 km wide and fog is opaque at 1100 m. Improve depth precision
 // without moving the collision mesh, road markings or the camera position.
 camera.far=2500;camera.updateProjectionMatrix();
 const q=queries();
 if(q.get('shadows')==='0')scene.traverse(o=>{if(o.isLight)o.castShadow=false;});
 if(q.get('paving')==='0'){const streets=scene.getObjectByName('streets');if(streets)streets.visible=false;const marks=scene.getObjectByName('RoadMarkings');if(marks)marks.visible=false;}
}
