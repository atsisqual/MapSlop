import {chromium} from 'playwright';
import fs from 'node:fs';
const b=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const root=process.env.MAPSLOP_RESULTS||'/tmp/lighting-fixture';
fs.mkdirSync(root,{recursive:true});
const report={pass:false,variants:{}};
try{
 for(const quality of ['off','low','high']){
  const p=await b.newPage({viewport:{width:640,height:480}});const errors=[];
  p.on('pageerror',e=>errors.push(e.message));p.on('console',m=>{if(m.type()==='error'&&!m.text().includes('favicon'))errors.push(m.text());});
  await p.goto('http://127.0.0.1:8080/');
  await p.evaluate(async quality=>{
   const THREE=await import('/vendor/three/build/three.webgpu.js');
   const {installLighting}=await import('/pedome-lighting.mjs');
   const renderer=new THREE.WebGPURenderer({forceWebGL:true,antialias:false});await renderer.init();renderer.setSize(640,480);document.body.appendChild(renderer.domElement);
   const scene=new THREE.Scene();scene.background=new THREE.Color(0xb8d4ef);
   const hemi=new THREE.HemisphereLight(0xffffff,0x77805d,2.2),sun=new THREE.DirectionalLight(0xfff0d8,2.4);sun.position.set(90,140,50);scene.add(hemi,sun);
   const group=new THREE.Group();scene.add(group);const cube=new THREE.Mesh(new THREE.BoxGeometry(8,10,8),new THREE.MeshStandardMaterial({color:0xbca788}));cube.position.y=5;group.add(cube);
   const plane=new THREE.Mesh(new THREE.PlaneGeometry(140,140),new THREE.MeshStandardMaterial({color:0x999999}));plane.rotation.x=-Math.PI/2;scene.add(plane);
   const cam=new THREE.PerspectiveCamera(45,640/480,.1,300);cam.position.set(25,22,35);cam.lookAt(0,0,0);
   const light=installLighting(scene,renderer,sun,hemi,group,quality);light.update(cam);renderer.render(scene,cam);await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
   window.qa={...light.report(),triangles:renderer.info.render.triangles};
  },quality);
  const s=await p.evaluate(()=>window.qa);await p.screenshot({path:root+'/'+quality+'.png'});
  report.variants[quality]={...s,errors};if(errors.length)throw Error(JSON.stringify(errors));
  if(quality!=='off'&&(!s.shadow_enabled||!s.sun_cast_shadow||s.casters!==1||s.updates!==1||!s.fog))throw Error(JSON.stringify(s));
  await p.close();
 }
 report.pass=true;
}catch(e){report.error=String(e);process.exitCode=1}
finally{fs.writeFileSync(root+'/report.json',JSON.stringify(report,null,2));console.log('LIGHTING_FIXTURE',JSON.stringify(report));await b.close()}
