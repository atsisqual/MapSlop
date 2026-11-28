import {chromium} from 'playwright';
import fs from 'node:fs';
const root=process.env.MAPSLOP_RESULTS||'/tmp/local-3d';
const url=process.env.MAPSLOP_TEST_URL||'http://127.0.0.1:8080/';
const report={pass:false,modes:{}};
const b=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
 for(const mode of ['glb','tiles']){
  const p=await b.newPage({viewport:{width:1000,height:750}});const errors=[],external=[];
  p.on('pageerror',e=>errors.push(e.message));p.on('console',m=>{if(m.type()==='error'&&!m.text().includes('favicon'))errors.push(m.text())});
  await p.route('**/*',r=>{const u=r.request().url();if(u.startsWith(new URL(url).origin+'/')||u.startsWith('blob:')||u.startsWith('data:'))return r.continue();external.push(u);return r.abort()});
  try{
   await p.goto(url+'?mode='+mode,{waitUntil:'load',timeout:60000});
   await p.waitForFunction(()=>window.localMesh?.ready||window.localMesh?.error,{},{timeout:90000});
   const s=await p.evaluate(()=>window.localMesh);
   await p.screenshot({path:root+'/church-'+mode+'.png'});
   const drift=Math.max(...s.bounds.flat().map((v,i)=>Math.abs(v-s.report.bounds.flat()[i])));
   report.modes[mode]={...s,drift,errors,external};
   if(s.error||!s.ready||s.models<1||drift>.05||errors.length||external.length||(s.report.materials&&(!s.pbr||s.pbr.length<2||s.pbr.some(m=>!m.uv||!m.normal||!m.roughness||!m.base))))throw Error(JSON.stringify(report.modes[mode]));
  }finally{await p.close()}
 }
 report.pass=true;
}catch(e){report.error=String(e);process.exitCode=1}
finally{fs.writeFileSync(root+'/viewer-report.json',JSON.stringify(report,null,2));console.log('LOCAL_3D_RESULT',JSON.stringify(report));await b.close()}
