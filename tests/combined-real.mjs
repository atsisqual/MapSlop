import {chromium} from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import {driveTerrainRoute} from './terrain-drive.mjs';
const root=process.env.MAPSLOP_RESULTS||'/tmp/ortho-results';
const reference=JSON.parse(fs.readFileSync('/tmp/ortho-terrain/road-validation.json')).carved_drive.route;
if(reference.way!==149303998||reference.points.length!==61)throw Error('Unexpected approved route');
const report={pass:false,errors:[],baseline:null,candidate:null,method:'Same approved terrain, buildings, trees and imagery in both builds; change only paving rules and fallback roof colour. Software rendering timings are diagnostic, not device FPS.'};
const save=()=>fs.writeFileSync(path.join(root,'combined-report.json'),JSON.stringify(report,null,2)+'\n');
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const near=v=>v?.applied&&v.level==='near'&&v.metres_per_pixel===.25&&v.alignment_error_m<.02;
const points=[{name:'rua-das-boucas',x:-465.15545,z:-359.49089,dx:-12,dz:10,h:16},{name:'igreja',x:0,z:0,dx:0,dz:0,h:30}];
async function run(port,suffix){
 const page=await browser.newPage({viewport:{width:823,height:384}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&!m.text().includes('favicon'))errors.push(m.text())});
 const url='http://127.0.0.1:'+port+'/?webgl';
 await page.route('**/*',r=>r.request().url().startsWith(new URL(url).origin+'/')?r.continue():r.abort());
 const settled=()=>page.waitForFunction(()=>window.mapslop.orthoPreview.ortho.report().settled,{},{timeout:120000});
 try{
  await page.goto(url,{waitUntil:'load',timeout:90000});
  await page.waitForFunction(()=>window.mapslop?.ready&&window.mapslop.vegetationPreview&&window.buildingDetailReport,{},{timeout:120000});await settled();
  await page.evaluate(()=>{const p=window.mapslop.orthoPreview;p.renderer.setAnimationLoop(null);const render=p.renderDrive;window.__frames=[];p.renderDrive=async(dt,t)=>{const start=performance.now();await render(dt,t);window.__frames.push(performance.now()-start);};});
  const drive=await page.evaluate(driveTerrainRoute,{reference,targetSpeed:5.5,renderEvery:15});
  const timing=await page.evaluate(async()=>{const m=window.mapslop,p=m.orthoPreview;for(let i=0;i<8;i++)await p.renderDrive(.05,performance.now()/1000);p.ortho.update(m.camera,true);const f=window.__frames.slice().sort((a,b)=>a-b);return {frames:f.length,median_ms:f[Math.floor(f.length/2)],p95_ms:f[Math.min(f.length-1,Math.floor(f.length*.95))]};});await settled();
  const driveTile=await page.evaluate(()=>{const m=window.mapslop,e=m.controllers.getActiveEntity();return m.orthoPreview.ortho.inspect(e.position.x,e.position.z);});
  const captures=[];
  for(const point of points){
   await page.evaluate(async({x,z,dx,dz,h})=>{
    const THREE=await import('three/webgpu');const {heightAt}=await import(new URL('js/terrain.js',location.href).href);const m=window.mapslop,p=m.orthoPreview,cam=new THREE.PerspectiveCamera(65,823/384,.1,600);
    cam.position.set(x+dx,heightAt(x,z)+h,z+dz);cam.up.set(0,0,-1);cam.lookAt(x,heightAt(x,z),z);cam.updateMatrixWorld(true);
    p.captureCam=cam;p.ortho.update(cam,true);m.vegetationPreview.vegetation.update(cam,true);
   },point);await settled();
   const capture=await page.evaluate(async({x,z})=>{const m=window.mapslop,p=m.orthoPreview;p.renderer.render(p.scene,p.captureCam);await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));return {tile:p.ortho.inspect(x,z),stream:p.ortho.report(),vegetation:m.vegetationPreview.vegetation.stats};},point);
   captures.push({...point,...capture});
   await page.screenshot({path:path.join(root,point.name+'-'+suffix+'.png'),timeout:60000});
  }
  const scene=await page.evaluate(async()=>{
   const m=window.mapslop,p=m.orthoPreview,l=p.scene.getObjectByName('streets').userData.layout;
   const {area}=await import(new URL('js/street-geometry.js',location.href).href);
   const areaSum=items=>items.reduce((s,v)=>s+Math.abs(area(v.p)),0),source=m.GEO.explicitPaving;
   const buildings=window.buildingDetailReport,rows=buildings.rows;
   const sideIds=[...new Set(l.sidewalks.list.map(v=>v.data?.osmWay??v.e?.osmWay??null))];
   // polygonIndex stores data on each item; use actual emitted polygon attribution.
   const pathIds=[...new Set(l.paths.list.map(v=>v.data?.osmWay??v.e?.osmWay??null))];
   return {paving:{sidewalk_count:l.sidewalks.list.length,sidewalk_m2:areaSum(l.sidewalks.list),path_count:l.paths.list.length,path_m2:areaSum(l.paths.list),asphalt_m2:areaSum(l.carriageways.list)+areaSum(l.service.list),sideIds,pathIds,source:source?{sidewalkIds:Object.keys(source.sidewalks),pathIds:Object.keys(source.paths),areaIds:[...new Set(source.areas.map(a=>String(a.id)))]}:null},buildings,roof_counts:rows.reduce((a,r)=>{if(r.policy!=='roofer_lod22'){const k=r.roof_color?.class||'unknown';a[k]=(a[k]||0)+1;}return a;},{}),vegetation:m.vegetationPreview.vegetation.stats};
  });
  return {drive:{success:drive.success,reason:drive.reason,distance_m:drive.distance_m,progress_m:drive.progress_m,collisions:drive.collisions,contact_max_m:drive.contact_max_m,surface_contact_max_m:drive.surface_contact_max_m,max_cross_track_m:drive.max_cross_track_m,vertical:drive.vertical_metrics?.surface_window_0_2s?.max_m_s2,roll:drive.vertical_metrics?.straight_roll_max_degrees},timing,driveTile,captures,scene,errors};
 }finally{await page.close();}
}
try{
 report.baseline=await run(8080,'before');save();
 report.candidate=await run(8081,'after');save();
 const a=report.baseline,b=report.candidate,p=b.scene.paving,bs=b.scene.buildings,source=p.source;
 const validDrive=d=>d.success&&d.progress_m>=104&&d.distance_m>=100&&d.collisions===0&&d.contact_max_m<=.5&&d.surface_contact_max_m<=.5;
 const budget=v=>v.total===5702&&v.draw_calls<=72&&v.triangles<=350000;
 const measuredRejected=bs.measured_diagnostics.filter(r=>r.policy!=='roofer_lod22');
 report.checks={
  no_errors:!a.errors.length&&!b.errors.length,
  same_asphalt:Math.abs(p.asphalt_m2-a.scene.paving.asphalt_m2)<.01,
  explicit_sidewalks:p.sidewalk_count>0&&p.sideIds.every(v=>v!==null&&source.sidewalkIds.includes(String(v))),
  explicit_paths:p.pathIds.every(v=>v!==null&&(source.pathIds.includes(String(v))||source.areaIds.includes(String(v)))),
  fewer_sidewalks:p.sidewalk_m2<a.scene.paving.sidewalk_m2*.5,
  roof_colors:b.scene.roof_counts.terracotta>0&&b.scene.roof_counts.gray>0&&bs.rows.every(r=>r.policy==='roofer_lod22'||r.roof_color&&(r.roof_color.class==='unknown'||r.roof_color.samples>=4&&r.roof_color.inner_margin_m>=.35)),
  buildings:bs.buildings===527&&bs.foundation_failures.length===0&&bs.measured>=17&&bs.measured_diagnostics.length===18&&measuredRejected.every(r=>String(r.osm_id)==='223354671'&&r.reason==='roof_intersects_local_terrain')&&bs.shell_triangles<=120000&&bs.all_triangles<=250000&&bs.building_draw_calls<=40,
  drive:validDrive(a.drive)&&validDrive(b.drive)&&b.drive.vertical<=Math.max(a.drive.vertical+.1,2.958)&&b.drive.roll<=Math.max(a.drive.roll+.05,.429),
  texture:near(b.driveTile)&&b.captures.every(c=>near(c.tile)&&c.stream.settled&&c.stream.estimated_texture_bytes<=24000000),
  vegetation:b.captures.every(c=>budget(c.vegetation)),
  performance:b.timing.frames>=70&&a.timing.frames>=70&&b.timing.median_ms<=a.timing.median_ms*1.5&&b.timing.p95_ms<=a.timing.p95_ms*2
 };
 report.pass=Object.values(report.checks).every(Boolean);console.log('COMBINED_RESULT',JSON.stringify({pass:report.pass,checks:report.checks,before:a.timing,after:b.timing,paving:p,roof_counts:b.scene.roof_counts,measured:bs.measured,drive:b.drive}));if(!report.pass)process.exitCode=1;
}catch(e){report.errors.push(String(e));console.error(e);process.exitCode=1;}finally{save();await browser.close();}
