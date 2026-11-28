import {chromium} from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
const out=process.env.MAPSLOP_RESULTS||'/tmp/vegetation-results',url=process.env.MAPSLOP_TEST_URL||'http://127.0.0.1:8080/?webgl';
const report={budget:{vegetation_draw_calls:72,vegetation_triangles:350000,visible_trees_per_candidate:1,lod_m:[100,250,750],target_device:'30 FPS mobile / 60 FPS desktop; software renderer timings are diagnostic only'},samples:[],errors:[],pass:false};
const save=()=>fs.writeFileSync(path.join(out,'vegetation-visual-report.json'),JSON.stringify(report,null,2)+'\n');
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:823,height:384}});
page.on('pageerror',e=>report.errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&!m.text().includes('404'))report.errors.push(m.text())});
await page.route('**/*',r=>r.request().url().startsWith(new URL(url).origin+'/')?r.continue():r.abort());
try{
 await page.goto(url,{waitUntil:'load',timeout:90000});
 await page.waitForFunction(()=>window.mapslop?.ready&&window.mapslop.vegetationPreview,{},{timeout:120000});
 await page.screenshot({path:path.join(out,'game-spawn-vegetation.png'),timeout:60000});
 const initial=await page.evaluate(()=>{const {vegetation,renderer}=window.mapslop.vegetationPreview;renderer.setAnimationLoop(null);return vegetation.stats;});
 report.initial=initial;save();
 const ortho=JSON.parse(fs.readFileSync(path.join(out,'ortho-comparison.json')));
 const positions=ortho.crops.filter(c=>c.name!=='pilot');
 for(const {name,world_extent:[x0,z0,x1,z1]} of positions){
  const sample=await page.evaluate(async({x,z})=>{
   const THREE=await import('three/webgpu');
   const {heightAt}=await import(new URL('js/terrain.js',location.href).href);
   const {renderer,scene,vegetation}=window.mapslop.vegetationPreview;
   const cam=new THREE.PerspectiveCamera(62,823/384,.1,1500);
   cam.position.set(x,heightAt(x,z)+9,z+55);cam.lookAt(x,heightAt(x,z)+7,z);
   const stats=vegetation.update(cam,true);
   const frame=()=>new Promise(r=>requestAnimationFrame(r));
   const render=async visible=>{
    vegetation.group.visible=visible;renderer.render(scene,cam);await frame();
    const times=[];for(let i=0;i<8;i++){const start=performance.now();renderer.render(scene,cam);await frame();times.push(performance.now()-start);}
    times.sort((a,b)=>a-b);
    return {median_ms:times[4],p95_ms:times[7],frames_ms:times,renderer_draw_calls:renderer.info.render.drawCalls??renderer.info.render.calls??null,renderer_triangles:renderer.info.render.triangles??null};
   };
   const baseline=await render(false),withTrees=await render(true);
   renderer.render(scene,cam);await frame();
   window.mapslop.vegetationPreview.captureCam=cam;
   return {stats,baseline,withTrees};
  },{x:(x0+x1)/2,z:(z0+z1)/2});
  await page.screenshot({path:path.join(out,name+'-game-trees.png'),timeout:60000});
  await page.evaluate(()=>{const p=window.mapslop.vegetationPreview;p.vegetation.group.visible=false;p.renderer.render(p.scene,p.captureCam);});
  await page.screenshot({path:path.join(out,name+'-game-no-trees.png'),timeout:60000});
  await page.evaluate(async({x,z})=>{
   const THREE=await import('three/webgpu');const {heightAt}=await import(new URL('js/terrain.js',location.href).href);
   const p=window.mapslop.vegetationPreview,cam=new THREE.OrthographicCamera(-60,60,60*384/823,-60*384/823,.1,600);
   cam.position.set(x,heightAt(x,z)+180,z);cam.up.set(0,0,-1);cam.lookAt(x,heightAt(x,z),z);p.vegetation.group.visible=true;p.vegetation.update(cam,true);p.renderer.render(p.scene,cam);
  },{x:(x0+x1)/2,z:(z0+z1)/2});
  await page.screenshot({path:path.join(out,name+'-game-topdown.png'),timeout:60000});
  report.samples.push({name,...sample});save();
 }
 const expected=JSON.parse(fs.readFileSync(path.join(out,'vegetation-candidates.json'))).trees.length;
 const check=s=>s.total===expected&&s.visible>0&&s.visible<=expected&&s.lod_counts.reduce((a,b)=>a+b,0)===s.visible&&s.draw_calls<=report.budget.vegetation_draw_calls&&s.triangles<=report.budget.vegetation_triangles;
 report.pass=positions.length>=2&&check(initial)&&report.samples.every(s=>check(s.stats))&&report.samples.some(s=>s.stats.lod_counts.every(n=>n>0))&&report.errors.length===0;
 console.log('VEGETATION_VISUAL',JSON.stringify(report));
 if(!report.pass)process.exitCode=1;
}catch(e){report.errors.push(String(e));process.exitCode=1;console.error(e);}
finally{save();await browser.close();}
