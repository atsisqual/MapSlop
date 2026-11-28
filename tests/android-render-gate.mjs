import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {chromium} from 'playwright';

const dir=process.env.MAPSLOP_RESULTS||'/tmp/pedome-results';
const base=new URL(process.env.MAPSLOP_TEST_URL);
const hardware=process.env.MAPSLOP_GPU==='hardware';
const tryWebGPU=process.env.MAPSLOP_GPU==='webgpu'||process.env.MAPSLOP_GPU==='hardware-webgpu';
const realGPU=hardware||process.env.MAPSLOP_GPU==='hardware-webgpu';
const mode=realGPU?(tryWebGPU?'hardware-webgpu':'hardware'):tryWebGPU?'webgpu':'swiftshader';
const args=realGPU?['--enable-gpu','--disable-software-rasterizer']:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'];
if(tryWebGPU)args.push('--enable-unsafe-webgpu');
await mkdir(dir,{recursive:true});
const browser=await chromium.launch({headless:true,args});
const result={mode,cases:[]};
try{
 if(tryWebGPU){
  const probe=await browser.newPage();
  const probeURL=new URL('/__gpu_probe__',base).href;
  await probe.route(probeURL,r=>r.fulfill({body:'<html></html>',contentType:'text/html'}));
  await probe.goto(probeURL);
  const available=await probe.evaluate(async()=>Boolean(await navigator.gpu?.requestAdapter({featureLevel:'compatibility'}).catch(()=>null)));
  await probe.close();
  if(!available){result.skipped='No WebGPU adapter on runner';console.log(result.skipped);}
 }
 if(!result.skipped)for(const [enabled,mips,srgb] of [[true,'offline',true],[true,'0',true],[true,'gpu',false],[true,'gpu',true],[false,'offline',true]]){
  const url=new URL(base);url.search='';url.searchParams.set('debug','1');url.searchParams.set('mips',mips);if(!srgb)url.searchParams.set('srgb','0');
  if(!tryWebGPU)url.searchParams.set('renderer','webgl');
  if(!enabled)url.searchParams.set('ortho','0');
  const page=await browser.newPage({viewport:{width:823,height:384},isMobile:true,hasTouch:true,userAgent:'Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/142.0 Mobile Safari/537.36'});
  const errors=[],requests=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error'&&!m.text().includes('favicon'))errors.push(m.text())});
  page.on('request',r=>{if(new URL(r.url()).pathname.includes('/ortho/'))requests.push(r.url())});
  await page.goto(url.href,{waitUntil:'load',timeout:90000});
  try{await page.waitForFunction(()=>window.mapslop?.ready&&window.mapslop?.renderDebug&&window.mapslop.orthoPreview?.ortho.report().settled||document.querySelector('#status')?.textContent.startsWith('Erro:'),{},{timeout:120000,polling:250});}catch(e){
   const partial=await page.evaluate(()=>({status:document.querySelector('#status')?.textContent,ready:window.mapslop?.ready,stream:window.mapslop?.orthoPreview?.ortho.report(),hasDebug:!!window.mapslop?.renderDebug,backend:window.mapslop?.orthoPreview?.renderer.backend.isWebGPUBackend?'WebGPU':'other'})).catch(()=>null);
   result.cases.push({enabled,partial,errors,orthoRequests:requests.length});console.error('ANDROID_GATE_TIMEOUT',JSON.stringify(result.cases.at(-1)));throw e;
  }
  assert.ok(!(await page.locator('#status').textContent()).startsWith('Erro:'),await page.locator('#status').textContent());
  const state=await page.evaluate(async()=>{
   const m=window.mapslop,b=m.orthoPreview.renderer.backend;
   await b.device?.queue?.onSubmittedWorkDone();
   const p=m.controllers.getActiveEntity().position;
   return {...m.renderDebug(),tile:m.orthoPreview.ortho.inspect(p.x,p.z),offsets:m.orthoPreview.ortho.group.children.map(o=>o.position.y)};
  });
  result.cases.push({enabled,mips,srgb,state,errors,orthoRequests:requests.length});
  await page.screenshot({path:join(dir,'android-'+mode+'-'+(enabled?mips+'-'+srgb:'no-ortho')+'.png')});
  assert.equal(state.orthoEnabled,enabled);
  assert.equal(state.baseGroundVisible,!enabled);
  assert.equal(state.far,2500);
  assert.deepEqual(errors,[]);assert.deepEqual(state.errors,[]);
  assert.equal(state.backend,tryWebGPU?'WebGPU':'WebGL2');
  if(realGPU&&!tryWebGPU)assert.ok(state.gpu.renderer&&!/swiftshader|llvmpipe|softpipe|software|lavapipe/i.test(state.gpu.renderer),'No verified hardware renderer');
  if(realGPU&&tryWebGPU)assert.ok(state.gpu.isFallbackAdapter!==true&&!/swiftshader|llvmpipe|lavapipe|software/i.test(JSON.stringify(state.gpu)),'Software WebGPU adapter');
  if(enabled){
   assert.ok(state.tile?.applied&&state.tile.level==='near','Spawn tile missing');
   assert.deepEqual(state.tile.texture_px,[512,512]);assert.equal(state.tile.metres_per_pixel,132/512);
   assert.ok(state.tile.alignment_error_m<.02,'World/UV alignment regression');
   assert.ok(state.offsets.length>0&&state.offsets.every(x=>x===-.02),'Visual separation missing');
   assert.ok(state.textures.length>=64,'Missing texture rows');
   for(const t of state.textures){
    assert.ok(t.pot&&t.mipMode===mips&&t.generateMipmaps===(mips==='gpu')&&t.autoUpdate===(mips==='gpu')&&t.minFilter===(mips==='0'?1006:1008)&&t.magFilter===1006&&t.shaderSRGB===!srgb,'Invalid texture: '+JSON.stringify(t));
    if(mips==='offline')assert.equal(t.manualLevels,t.expectedLevels);
    if(mips!=='gpu')assert.equal(t.generated,false);
    assert.equal(t.anisotropy,1,'Android conservative sampler not applied');
    if(t.uploadedLevels&&state.backend==='WebGPU')assert.equal(t.gpuLevels,mips==='0'?1:t.expectedLevels,'Incomplete GPU mip allocation');
    if(t.uploadedLevels&&mips==='offline')assert.equal(t.uploadedLevels,t.expectedLevels,'Incomplete manual upload');
    if(t.uploadedLevels&&!srgb)assert.equal(t.internalFormat,state.backend==='WebGL2'?32856:'rgba8unorm','Unexpected linear RGBA8 format');
   }
   if(mips==='gpu')assert.ok(state.textures.some(t=>t.generated&&t.name===state.tile.texture_name),'No backend mip generation for the rendered near tile');
   else assert.ok(state.textures.some(t=>t.uploadedLevels===(mips==='offline'?t.expectedLevels:1)&&t.name===state.tile.texture_name),'No explicit near texture upload');
  }else{
   assert.equal(requests.length,0,'Ortho disabled but tiles fetched');
   assert.equal(state.textures.length,0,'Archived plain ground should not have a texture');
  }
  await page.close();
 }
 result.webgpuExercised=result.cases.some(c=>c.state.backend==='WebGPU');
 result.pass=!result.skipped;
 console.log('ANDROID_RENDER_GATE',mode,JSON.stringify(result.cases.map(c=>({enabled:c.enabled,backend:c.state.backend,gpu:c.state.gpu,textures:c.state.textures.length,generated:c.state.textures.filter(t=>t.generated).length}))));
}finally{
 await writeFile(join(dir,'android-'+mode+'.json'),JSON.stringify(result,null,2)+'\n');
 await browser.close();
}
