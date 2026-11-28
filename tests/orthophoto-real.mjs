import {chromium} from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
const out=process.env.MAPSLOP_RESULTS||'/tmp/ortho-results',url=process.env.MAPSLOP_TEST_URL||'http://127.0.0.1:8080/?webgl';
const report={errors:[],views:[],pass:false,budget:{max_initial_requested_bytes:2500000,max_estimated_texture_bytes:24000000,max_near:8,max_mid:20}};
const save=()=>fs.writeFileSync(path.join(out,'orthophoto-render-report.json'),JSON.stringify(report,null,2)+'\n');
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:823,height:384}});
page.on('pageerror',e=>report.errors.push(e.message));
page.on('console',m=>{if(m.type()==='error'&&!m.text().includes('favicon'))report.errors.push(m.text())});
await page.route('**/*',r=>r.request().url().startsWith(new URL(url).origin+'/')?r.continue():r.abort());
const settled=()=>page.waitForFunction(()=>window.mapslop.orthoPreview.ortho.report().settled,{},{timeout:120000});
try{
 await page.goto(url,{waitUntil:'load',timeout:90000});
 await page.waitForFunction(()=>window.mapslop?.ready&&window.mapslop.orthoPreview,{},{timeout:120000});
 await settled();
 report.initial=await page.evaluate(()=>window.mapslop.orthoPreview.ortho.report());
 await page.screenshot({path:path.join(out,'ortho-spawn.png'),timeout:60000});
 // Real keyboard movement while render loop and LOD update remain active.
 await page.evaluate(()=>{const e=window.mapslop.controllers.getActiveEntity();window.__orthoDrive={start:[e.position.x,e.position.z],frames:[],on:true};let last=performance.now();function tick(now){if(!window.__orthoDrive.on)return;window.__orthoDrive.frames.push(now-last);last=now;requestAnimationFrame(tick)}requestAnimationFrame(tick)});
 await page.keyboard.down('w');
 try{await page.waitForFunction(()=>{const p=window.mapslop.controllers.getActiveEntity().position,s=window.__orthoDrive.start;return Math.hypot(p.x-s[0],p.z-s[1])>=12},{},{timeout:90000});}finally{await page.keyboard.up('w')}
 report.drive=await page.evaluate(()=>{
  const d=window.__orthoDrive;d.on=false;const p=window.mapslop.controllers.getActiveEntity().position,f=d.frames.sort((a,b)=>a-b);
  return {distance_m:Math.hypot(p.x-d.start[0],p.z-d.start[1]),frames:f.length,median_ms:f[Math.floor(f.length/2)],p95_ms:f[Math.floor(f.length*.95)],software_renderer_only:true};
 });
 await settled();
 await page.screenshot({path:path.join(out,'ortho-driving.png'),timeout:60000});
 const points=await page.evaluate(()=>{
  const g=window.mapslop.GEO,roads=g.roads.filter(r=>r.name==='Via Intermunicipal'||r.name==='Avenida Humberto Delgado');
  const coords=roads.flatMap(r=>Array.from({length:r.pts.length/2},(_,i)=>[r.pts[2*i],r.pts[2*i+1]]));
  const t=g.terrain;
  const p=coords.find(([x,z])=>x>t.x0+50&&z>t.z0+50&&x<t.x0+(t.nx-1)*t.cell-50&&z<t.z0+(t.nz-1)*t.cell-50);
  return [{name:'igreja',x:0,z:0},...(p?[{name:'via-intermunicipal',x:p[0],z:p[1]}]:[])];
 });
 if(points.length<2)throw Error('Missing real second alignment control point');
 await page.evaluate(()=>window.mapslop.orthoPreview.renderer.setAnimationLoop(null));
 for(const point of points){
  const v=await page.evaluate(async({x,z})=>{
   const THREE=await import('three/webgpu');const {heightAt}=await import(new URL('js/terrain.js',location.href).href);
   const p=window.mapslop.orthoPreview,cam=new THREE.OrthographicCamera(-70,70,70*384/823,-70*384/823,.1,600);
   cam.position.set(x,heightAt(x,z)+150,z);cam.up.set(0,0,-1);cam.lookAt(x,heightAt(x,z),z);
   p.ortho.update(cam,true);
   const m=p.ortho.manifest,tile=m.tiles.find(t=>x>=t.bounds[0]&&x<t.bounds[2]&&z>=t.bounds[1]&&z<t.bounds[3]);
   const g=p.ortho.group;let maxHeightError=0,samples=0;
   for(const mesh of g.children){
    const a=mesh.geometry.attributes.position;
    for(let i=0;i<a.count;i+=Math.max(1,Math.floor(a.count/8))){maxHeightError=Math.max(maxHeightError,Math.abs(a.getY(i)-heightAt(a.getX(i),a.getZ(i))));samples++;}
   }
   p.captureCam=cam;
   return {tile:tile?.bounds,uv:tile?[(x-tile.bounds[0]+m.gutter_m)/(m.tile_m+2*m.gutter_m),1-(z-tile.bounds[1]+m.gutter_m)/(m.tile_m+2*m.gutter_m)]:null,max_height_error_m:maxHeightError,samples};
  },point);
  await settled();
  await page.evaluate(()=>{const p=window.mapslop.orthoPreview;p.renderer.render(p.scene,p.captureCam)});
  await page.screenshot({path:path.join(out,point.name+'-ortho-game.png'),timeout:60000});
  // Same exact camera, photo alone and with 3D objects: visual registration evidence.
  await page.evaluate(()=>{const p=window.mapslop.orthoPreview;p.hidden=p.scene.children.filter(o=>o.visible&&o!==p.ortho.group&&!o.isLight);for(const o of p.hidden)o.visible=false;p.renderer.render(p.scene,p.captureCam)});
  await page.screenshot({path:path.join(out,point.name+'-ortho-only.png'),timeout:60000});
  await page.evaluate(()=>{const p=window.mapslop.orthoPreview;for(const o of p.hidden)o.visible=true;});
  report.views.push({...point,...v,stream:await page.evaluate(()=>window.mapslop.orthoPreview.ortho.report())});save();
 }
 report.network=await page.evaluate(()=>performance.getEntriesByType('resource').filter(r=>r.name.includes('/ortho/')).map(r=>({name:new URL(r.name).pathname,transferSize:r.transferSize,encodedBodySize:r.encodedBodySize})));
 const check=s=>s.settled&&!s.errors.length&&s.counts.near<=8&&s.counts.mid<=20&&s.estimated_texture_bytes<=report.budget.max_estimated_texture_bytes&&s.counts.near>0;
 report.pass=check(report.initial)&&report.initial.bytes_requested<=report.budget.max_initial_requested_bytes&&report.drive.distance_m>=12&&report.views.every(v=>v.tile&&v.uv.every(u=>u>0&&u<1)&&v.samples>0&&v.max_height_error_m<.05&&check(v.stream))&&!report.errors.length;
 console.log('ORTHOPHOTO_RENDER',JSON.stringify({...report,network:report.network.length}));if(!report.pass)process.exitCode=1;
}catch(e){report.errors.push(String(e));process.exitCode=1;console.error(e)}
finally{save();await browser.close();}
