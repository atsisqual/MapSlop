import * as THREE from 'three/webgpu';
import {texture,vec4,mix,step} from 'three/tsl';

const generated=new WeakSet(),uploaded=new WeakMap();
const queries=()=>new URLSearchParams(location.search);
export const isPOT=n=>Number.isInteger(n)&&n>0&&Number.isInteger(Math.log2(n));
export function rendererOptions(){
 const q=queries();
 return {antialias:true,forceWebGL:!navigator.gpu||q.has('webgl')||q.get('renderer')==='webgl'};
}
export function groundPolicy(renderer){
 const q=queries(),b=renderer.backend;let gpu='';
 if(b.isWebGLBackend){const gl=b.gl,e=gl.getExtension('WEBGL_debug_renderer_info');gpu=String(gl.getParameter(e?e.UNMASKED_RENDERER_WEBGL:gl.RENDERER));}
 else gpu=JSON.stringify(b.device?.adapterInfo||{});
 const explicit=q.get('mips');
 return {mips:['0','gpu','offline'].includes(explicit)?explicit:q.get('srgb')==='0'?'gpu':/xclipse/i.test(gpu)?'0':'offline',srgb:q.get('srgb')!=='0',gpu};
}
export async function loadOfflineTexture(root,data){
 const d=data.offline;if(!d||d.format!=='rgba8-bottom-up-srgb-gzip-v1')throw Error('Missing offline mip chain '+data.path);
 const res=await fetch(new URL(d.path,root));if(!res.ok)throw Error('Missing offline mip pack '+d.path);
 const packed=await res.arrayBuffer();if(packed.byteLength!==d.bytes)throw Error('Invalid mip pack size');
 const raw=await new Response(new Blob([packed]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
 let offset=0;const mips=d.levels.map((m,i)=>{
  const n=data.px>>i;if(m.px!==n||m.bytes!==n*n*4||offset+m.bytes>raw.byteLength)throw Error('Invalid mip chain dimensions');
  const image={data:new Uint8Array(raw,offset,m.bytes),width:n,height:n};offset+=m.bytes;return image;
 });
 if(mips.length!==1+Math.log2(data.px)||offset!==raw.byteLength)throw Error('Incomplete mip chain');
 const t=new THREE.DataTexture(mips[0].data,data.px,data.px,THREE.RGBAFormat,THREE.UnsignedByteType);
 t.mipmaps=mips;t.flipY=false;return t;
}
export function setGroundMap(material,tex,renderer){
 material.map=tex;
 if(tex&&!groundPolicy(renderer).srgb){
  if(!material.isNodeMaterial)throw Error('Terrain shader conversion requires NodeMaterial');
  const c=texture(tex).rgb;
  material.colorNode=vec4(mix(c.div(12.92),c.add(.055).div(1.055).pow(2.4),step(.04045,c)),1);
 }else if(material.isNodeMaterial)material.colorNode=null;
 material.needsUpdate=true;
}
export function configureGroundTexture(tex,renderer){
 const max=Math.max(1,renderer.getMaxAnisotropy()||1);
 const mobile=/Android/i.test(navigator.userAgent);
 const requested=Number(queries().get('anisotropy')|| (mobile?1:8));
 const policy=groundPolicy(renderer);
 // Dynamic procedural CanvasTexture has no archived pixels. Avoid GPU generation;
 // when offline is selected, create CPU mip levels from its painted base.
 if(policy.mips==='offline'&&tex.isCanvasTexture&&tex.mipmaps.length===0){
  let prev=tex.image;tex.mipmaps=[prev];
  while(prev.width>1||prev.height>1){const c=document.createElement('canvas');c.width=Math.max(1,prev.width>>1);c.height=Math.max(1,prev.height>>1);c.getContext('2d').drawImage(prev,0,0,c.width,c.height);tex.mipmaps.push(c);prev=c;}
 }
 const mode=policy.mips==='offline'&&tex.mipmaps.length===0?'0':policy.mips;
 tex.userData={...tex.userData,mipMode:mode,shaderSRGB:!policy.srgb};
 tex.generateMipmaps=mode==='gpu';tex.mipmapsAutoUpdate=mode==='gpu';
 tex.minFilter=mode==='0'?THREE.LinearFilter:THREE.LinearMipmapLinearFilter;tex.magFilter=THREE.LinearFilter;
 tex.colorSpace=policy.srgb?THREE.SRGBColorSpace:THREE.NoColorSpace;
 tex.internalFormat=null; // NoColorSpace + RGBA/UnsignedByte => RGBA8; shader performs sRGB EOTF.
 if(mode==='0')tex.mipmaps=[];
 tex.anisotropy=mode==='0'?1:Math.min(max,Math.max(1,Number.isFinite(requested)?Math.floor(requested):1));
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
  generated:generated.has(tex),uploadedLevels:uploaded.get(tex)??0,internalFormat:b.isWebGLBackend?(data.glInternalFormat??null):(data.textureDescriptorGPU?.format??null),mipMode:tex.userData?.mipMode,manualLevels:tex.mipmaps.length,colorSpace:tex.colorSpace,shaderSRGB:tex.userData?.shaderSRGB??false};
}
export async function installRenderDiagnostics(renderer){
 const b=renderer.backend, original=b.generateMipmaps;
 if(typeof original!=='function')throw Error('Unknown mipmap backend');
 b.generateMipmaps=function(texture,...args){
  const result=original.call(this,texture,...args);
  generated.add(texture);return result;
 };
 const update=b.updateTexture;
 if(typeof update!=='function')throw Error('Unknown texture upload backend');
 b.updateTexture=function(tex,...args){const result=update.call(this,tex,...args);uploaded.set(tex,tex.mipmaps.length||1);return result;};
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
   if(s){const t=s.textures;panel.textContent=JSON.stringify({...s,textures:{count:t.length,generated:t.filter(x=>x.generated).length,invalid:t.filter(x=>!x.pot||(x.mipMode==='0'?(x.generateMipmaps||x.minFilter!==1006):x.mipMode==='offline'?(x.generateMipmaps||!x.trilinear||x.manualLevels!==x.expectedLevels):(!x.generateMipmaps||!x.trilinear))).length,sample:t.find(x=>x.generated)||t[0]||null}},null,1);}
  };
  setInterval(update,1000);
 }
 return (scene,ortho,camera)=>{
  const textures=new Set();
  scene.traverse(o=>{if(o.name==='ground'||o.name.startsWith('Ortho-')||['asphalt','sidewalks','footpaths','kerbs'].includes(o.name))for(const m of (Array.isArray(o.material)?o.material:[o.material]))if(m?.map)textures.add(m.map);});
  return {backend,gpu,groundPolicy:groundPolicy(renderer),maxAnisotropy:renderer.getMaxAnisotropy(),orthoEnabled:ortho?.group?.visible??false,
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
