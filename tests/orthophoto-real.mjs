import {chromium} from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import {driveTerrainRoute} from './terrain-drive.mjs';
const out=process.env.MAPSLOP_RESULTS||'/tmp/ortho-results',url=process.env.MAPSLOP_TEST_URL||'http://127.0.0.1:8080/?webgl';
const reference=JSON.parse(fs.readFileSync(process.env.MAPSLOP_ROAD_REPORT||'/tmp/ortho-terrain/road-validation.json')).carved_drive.route;
if(reference.way!==149303998||reference.points.length!==61)throw Error('Missing approved reference route');
const report={errors:[],views:[],pass:false,budget:{max_initial_requested_bytes:2500000,max_estimated_texture_bytes:24000000,max_near:8,max_mid:20},alignment_method:'Raycast actual partition mesh UV; inverse map to world and nearest image pixel centre. Not independent photo-feature/OSM survey error; paired evidence for visual review.'};
const save=()=>fs.writeFileSync(path.join(out,'orthophoto-render-report.json'),JSON.stringify(report,null,2)+'\n');
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:823,height:384}});
page.on('pageerror',e=>report.errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&!m.text().includes('favicon'))report.errors.push(m.text())});
await page.route('**/*',r=>r.request().url().startsWith(new URL(url).origin+'/')?r.continue():r.abort());
const settled=()=>page.waitForFunction(()=>window.mapslop.orthoPreview.ortho.report().settled,{},{timeout:120000});
const screenshot=name=>page.screenshot({path:path.join(out,name+'.png'),timeout:60000});
const near=v=>v?.applied===true&&v.level==='near'&&v.metres_per_pixel===.25&&v.texture_px.every(n=>n===528)&&Number.isFinite(v.alignment_error_m)&&v.alignment_error_m<.02&&Number.isFinite(v.pixel_center_error_m)&&v.pixel_center_error_m<=.18;
async function renderFinal(){
 await page.evaluate(async()=>{const p=window.mapslop.orthoPreview;p.renderer.render(p.scene,p.captureCam||window.mapslop.camera);await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));});
}
async function onlyGround(on){
 await page.evaluate(on=>{const p=window.mapslop.orthoPreview;if(on){p.hidden=p.scene.children.filter(o=>o.visible&&o!==p.ortho.group&&!o.isLight);for(const o of p.hidden)o.visible=false;}else{for(const o of p.hidden||[])o.visible=true;}},on);
 await renderFinal();
}
try{
 await page.goto(url,{waitUntil:'load',timeout:90000});
 await page.waitForFunction(()=>window.mapslop?.ready&&window.mapslop.orthoPreview,{},{timeout:120000});
 await settled();
 report.initial=await page.evaluate(()=>window.mapslop.orthoPreview.ortho.report());
 await screenshot('ortho-spawn');
 await page.evaluate(()=>{const p=window.mapslop.orthoPreview;p.renderer.setAnimationLoop(null);const render=p.renderDrive;window.__orthoFrames=[];p.renderDrive=async(dt,t)=>{const start=performance.now();await render(dt,t);window.__orthoFrames.push(performance.now()-start);};});
 report.drive=await page.evaluate(driveTerrainRoute,{reference,targetSpeed:5.5,renderEvery:15});
 report.drive_render=await page.evaluate(async()=>{
  const m=window.mapslop,p=m.orthoPreview;
  // Advance follow camera and LOD at the final real vehicle location, no teleport.
  for(let i=0;i<8;i++)await p.renderDrive(.05,performance.now()/1000);
  p.ortho.update(m.camera,true);
  const f=window.__orthoFrames.slice().sort((a,b)=>a-b);
  const e=m.controllers.getActiveEntity();return {frames:f.length,median_ms:f[Math.floor(f.length/2)],p95_ms:f[Math.min(f.length-1,Math.floor(f.length*.95))],software_renderer_only:true,end:{x:e.position.x,z:e.position.z},camera:{x:m.camera.position.x,z:m.camera.position.z}};
 });
 await settled();await renderFinal();
 report.drive_stream=await page.evaluate(()=>{const m=window.mapslop,p=m.orthoPreview,e=m.controllers.getActiveEntity(),cam=m.camera.position;return {stream:p.ortho.report(),vehicle:p.ortho.inspect(e.position.x,e.position.z),camera:p.ortho.inspect(cam.x,cam.z)};});
 if(!near(report.drive_stream.vehicle)||!near(report.drive_stream.camera))throw Error('25 cm texture not actually applied at final car/camera');
 await screenshot('ortho-driving');
 await onlyGround(true);await screenshot('ortho-driving-ground-only');await onlyGround(false);
 save();
 const points=await page.evaluate(reference=>{
  const g=window.mapslop.GEO,t=g.terrain;
  const xmax=t.x0+(t.nx-1)*t.cell,zmax=t.z0+(t.nz-1)*t.cell;
  const margin=(x,z)=>Math.min(x-t.x0,xmax-x,z-t.z0,zmax-z);
  const roads=g.roads.filter(r=>/via intermunicipal|humberto delgado|\bVIM\b/i.test(r.name||'')||[657862468,1245835693,303572277,303572242,1473693891,1473693893,1473693896,303572291,1479346973].includes(r.id));
  const candidates=[];
  for(const r of roads)for(let i=2;i<r.pts.length;i+=2){
   const a=[r.pts[i-2],r.pts[i-1]],b=[r.pts[i],r.pts[i+1]],len=Math.hypot(b[0]-a[0],b[1]-a[1]);
   if(len<4)continue;
   for(let k=1;k<=Math.max(1,Math.ceil(len/5));k++){const f=k/(Math.max(1,Math.ceil(len/5))+1),x=a[0]+f*(b[0]-a[0]),z=a[1]+f*(b[1]-a[1]),m=margin(x,z);
    if(m>=20)candidates.push({name:'via-intermunicipal',road:r.name||null,way:r.id,x,z,margin_m:m,selection:'interior sample of real OSM segment'});
   }
  }
  candidates.sort((a,b)=>b.margin_m-a.margin_m||a.way-b.way||a.x-b.x||a.z-b.z);
  const fallback=reference.points.map(v=>({name:'estrada-percurso-104m',road:reference.name,way:reference.way,x:v[0],z:v[1],margin_m:margin(v[0],v[1]),selection:'approved interior real OSM route fallback'})).filter(p=>p.margin_m>=40&&Math.hypot(p.x,p.z)>100).sort((a,b)=>b.margin_m-a.margin_m);
  const second=candidates[0]||fallback[0];
  return [{name:'igreja',way:149406360,x:0,z:0,margin_m:margin(0,0),selection:'documented origin of parish church'},...(second?[second]:[])];
 },reference);
 if(points.length!==2)throw Error('Missing interior real second alignment control point');
 for(const point of points){
  const coords=await page.evaluate(async({x,z})=>{
   const THREE=await import('three/webgpu');const {heightAt}=await import(new URL('js/terrain.js',location.href).href);
   const p=window.mapslop.orthoPreview,cam=new THREE.OrthographicCamera(-40,40,40*384/823,-40*384/823,.1,600);
   cam.position.set(x,heightAt(x,z)+150,z);cam.up.set(0,0,-1);cam.lookAt(x,heightAt(x,z),z);cam.updateMatrixWorld(true);
   p.ortho.update(cam,true);p.captureCam=cam;
   const [lat0,lon0]=p.ortho.manifest.origin_lat_lon,phi=lat0*Math.PI/180,A=6378137,E2=.00669437999014;
   const n=A/Math.sqrt(1-E2*Math.sin(phi)**2),m=A*(1-E2)/(1-E2*Math.sin(phi)**2)**1.5;
   const kx=Math.PI/180*n*Math.cos(phi),ky=Math.PI/180*m;
   let maxHeightError=0,samples=0;
   for(const mesh of p.ortho.group.children){const a=mesh.geometry.attributes.position;for(let i=0;i<a.count;i+=Math.max(1,Math.floor(a.count/8))){maxHeightError=Math.max(maxHeightError,Math.abs(a.getY(i)-heightAt(a.getX(i),a.getZ(i))));samples++;}}
   return {lat:lat0-z/ky,lon:lon0+x/kx,max_height_error_m:maxHeightError,samples};
  },point);
  await settled();await renderFinal();
  const v=await page.evaluate(({x,z})=>window.mapslop.orthoPreview.ortho.inspect(x,z),point);
  report.views.push({...point,...coords,...v,stream:await page.evaluate(()=>window.mapslop.orthoPreview.ortho.report())});save();
  await screenshot(point.name+'-ortho-game');
  await onlyGround(true);await screenshot(point.name+'-ortho-only');await onlyGround(false);
 }
 await page.evaluate(async()=>{
  const THREE=await import('three/webgpu'),{heightAt}=await import(new URL('js/terrain.js',location.href).href);
  const p=window.mapslop.orthoPreview,cam=new THREE.PerspectiveCamera(65,823/384,.1,600);
  cam.position.set(0,heightAt(0,0)+30,0);cam.up.set(0,0,-1);cam.lookAt(0,heightAt(0,0),0);cam.updateMatrixWorld(true);p.captureCam=cam;p.ortho.update(cam,true);
 });
 await settled();await renderFinal();
 report.church_low=await page.evaluate(()=>({height_above_origin_m:30,tile:window.mapslop.orthoPreview.ortho.inspect(0,0),stream:window.mapslop.orthoPreview.ortho.report()}));
 await screenshot('igreja-ortho-aerea-30m');await onlyGround(true);await screenshot('igreja-ortho-aerea-30m-only');await onlyGround(false);
 report.network=await page.evaluate(()=>performance.getEntriesByType('resource').filter(r=>r.name.includes('/ortho/')).map(r=>({name:new URL(r.name).pathname,transferSize:r.transferSize,encodedBodySize:r.encodedBodySize})));
 const check=s=>s.settled&&!s.errors.length&&s.counts.near<=8&&s.counts.mid<=20&&s.estimated_texture_bytes<=report.budget.max_estimated_texture_bytes&&s.counts.near>0;
 report.pass=check(report.initial)&&report.initial.bytes_requested<=report.budget.max_initial_requested_bytes&&report.drive.success&&report.drive.progress_m>=104&&report.drive.distance_m>=100&&check(report.drive_stream.stream)&&near(report.drive_stream.vehicle)&&near(report.drive_stream.camera)&&report.views.length===2&&report.views.every(v=>near(v)&&v.samples>0&&v.max_height_error_m<.05&&check(v.stream))&&near(report.church_low.tile)&&check(report.church_low.stream)&&!report.errors.length;
 console.log('ORTHOPHOTO_RENDER',JSON.stringify({pass:report.pass,initial:report.initial,drive:{way:report.drive.route.way,distance_m:report.drive.distance_m,progress_m:report.drive.progress_m,success:report.drive.success},drive_render:report.drive_render,drive_stream:report.drive_stream,views:report.views,church_low:report.church_low,errors:report.errors}));if(!report.pass)process.exitCode=1;
}catch(e){report.errors.push(String(e));process.exitCode=1;console.error(e)}
finally{save();await browser.close();}
