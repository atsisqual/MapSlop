// Private browser validation of actual generated road mesh, markings and controller.
// No teleport during a driven route; no change to production physics or OSM.
import {chromium} from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
const root=process.env.MAPSLOP_RESULTS||'/tmp/traffic-evidence';
const url=process.env.MAPSLOP_TEST_URL||'http://127.0.0.1:8080/?webgl';
fs.mkdirSync(root,{recursive:true});
const osm=JSON.parse(fs.readFileSync('data/pedome/pedome-osm.json','utf8'));
const tags=osm.elements.filter(e=>['roundabout','circular'].includes(e.tags?.junction)||e.tags?.highway==='mini_roundabout');
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1280,height:800}});
const report={source:'published TIN / pinned OSM',roundabout:{status:'blocked',reason:'No verified mapped roundabout in this pilot; do not substitute a fixture or a one-way junction',osm_tagged_features:tags.map(e=>({id:e.id,type:e.type,tags:e.tags}))},errors:[],console_errors:[],failed_requests:[],available_cases_pass:false};
const save=()=>fs.writeFileSync(path.join(root,'traffic-report.json'),JSON.stringify(report,null,2)+'\n');
page.on('pageerror',e=>report.errors.push(e.message));
page.on('console',m=>{if(m.type()==='error'||/GL_INVALID_OPERATION|GL_INVALID_FRAMEBUFFER_OPERATION|shader error/i.test(m.text()))report.console_errors.push(m.text())});
page.on('requestfailed',r=>report.failed_requests.push({url:r.url(),error:r.failure()?.errorText}));
await page.route('**/*',r=>r.request().url().startsWith(new URL(url).origin+'/')?r.continue():r.abort());
async function capture(name,x,z,span=65){
  await page.evaluate(async({x,z,span})=>{
    const THREE=await import('three/webgpu');
    const {heightAt}=await import(new URL('js/terrain.js',location.href).href);
    const {renderer,scene,getUI}=window.mapslop.trafficPreview;
    getUI().refresh();
    const cam=new THREE.OrthographicCamera(-span/2,span/2,span*800/1280/2,-span*800/1280/2,.1,500);
    cam.position.set(x,heightAt(x,z)+150,z);cam.up.set(0,0,-1);cam.lookAt(x,heightAt(x,z),z);
    cam.updateMatrixWorld();
    renderer.setAnimationLoop(()=>renderer.render(scene,cam));
    await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
  },{x,z,span});
  await page.screenshot({path:path.join(root,name+'.png'),timeout:60000});
  await page.evaluate(()=>window.mapslop.trafficPreview.renderer.setAnimationLoop(null));
}
try{
  await page.goto(url,{waitUntil:'load',timeout:90000});
  await page.waitForFunction(()=>window.mapslop?.ready===true&&!!window.mapslop.trafficPreview,{},{timeout:120000});
  const hudRead=()=>page.evaluate(()=>{
    const e=window.mapslop.controllers.getActiveEntity(),{x,z}=e.position;
    const canvas=document.querySelector('#hud-map canvas'),label=document.querySelector('#location');
    return {x,z,heading:e.heading,label:label.textContent,coords:label.title,marker:[Number(canvas.dataset.playerX),Number(canvas.dataset.playerZ)],expected_distance_m:Math.round(Math.hypot(x,z))};
  });
  const original=await hudRead();
  await page.evaluate(()=>{
    const {controllers:c,trafficPreview:p,GEO}=window.mapslop;
    const T=GEO.terrain,xmax=T.x0+(T.nx-1)*T.cell,zmax=T.z0+(T.nz-1)*T.cell;
    const target=GEO.roadGraph.nodes.filter(n=>Math.min(n.x-T.x0,xmax-n.x,n.z-T.z0,zmax-n.z)>45&&Math.hypot(n.x,n.z)>100).sort((a,b)=>Math.hypot(a.x,a.z)-Math.hypot(b.x,b.z))[0];
    if(!target)throw Error('Missing interior HUD validation target');
    c.teleportActiveTo(...p.roadSpawn(null,target.x,target.z).slice(0,3));
  });
  await page.waitForFunction(old=>{
    const e=window.mapslop.controllers.getActiveEntity(),{x,z}=e.position,canvas=document.querySelector('#hud-map canvas');
    return Math.hypot(x-old.x,z-old.z)>50&&Math.hypot(Number(canvas.dataset.playerX)-x,Number(canvas.dataset.playerZ)-z)<.5&&document.querySelector('#location').textContent.endsWith(' · '+Math.round(Math.hypot(x,z))+' m da igreja');
  },original,{timeout:15000});
  const moved=await hudRead();
  const consistent=r=>r.label.endsWith(' · '+r.expected_distance_m+' m da igreja')&&Math.hypot(r.marker[0]-r.x,r.marker[1]-r.z)<.5;
  report.hud={original,moved,pass:consistent(original)&&consistent(moved)&&original.label!==moved.label&&original.coords!==moved.coords};
  await page.screenshot({path:path.join(root,'hud-moved-live.png'),timeout:60000});
  await page.evaluate(({x,z,heading})=>window.mapslop.controllers.teleportActiveTo(x,z,heading),original);
  await page.waitForFunction(old=>document.querySelector('#location').textContent===old.label,original,{timeout:15000});
  await page.screenshot({path:path.join(root,'actual-game-spawn.png'),timeout:60000});
  const setup=await page.evaluate(async()=>{
    const {GEO,controllers:c,trafficPreview:p}=window.mapslop;
    p.renderer.setAnimationLoop(null);
    const T=GEO.terrain,RG=GEO.roadGraph;
    const xmax=T.x0+(T.nx-1)*T.cell,zmax=T.z0+(T.nz-1)*T.cell;
    const margin=(x,z)=>Math.min(x-T.x0,xmax-x,z-T.z0,zmax-z);
    const inside=(x,z)=>margin(x,z)>=35;
    const {heightAt}=await import(new URL('js/terrain.js',location.href).href);
    const {pavementLift,ROAD_Y}=await import(new URL('js/street-geometry.js',location.href).href);
    const {network,scene,roadSpawn}=p;
    const entity=c.getActiveEntity();
    const distance=(a,b)=>Math.hypot(a.x-b.x,a.z-b.z);
    const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
    const state=()=>({x:entity.position.x,y:entity.position.y,z:entity.position.z,heading:entity.heading,speed:entity.speed});
    const same=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1])<.05;
    const eligible=l=>!l.bridge&&!l.tunnel&&!l.layer&&['residential','unclassified','tertiary','secondary','living_street'].includes(l.kind);
    const segments=[];
    for(const l of RG.links.filter(eligible)){
      for(let i=0;i+2<l.pts.length;i+=2){
        const a={x:l.pts[i],z:l.pts[i+1]},b={x:l.pts[i+2],z:l.pts[i+3]};
        const len=distance(a,b);if(len<.01)continue;
        segments.push({l,a,b,len,dx:(b.x-a.x)/len,dz:(b.z-a.z)/len});
      }
    }
    function projection(s,x,z){
      const t=clamp((x-s.a.x)*s.dx+(z-s.a.z)*s.dz,0,s.len);
      const px=s.a.x+s.dx*t,pz=s.a.z+s.dz*t;
      return {x:px,z:pz,d:Math.hypot(x-px,z-pz)};
    }
    function nearest(x,z,name){
      return segments.filter(s=>!name||s.l.name===name).map(s=>({s,...projection(s,x,z)})).sort((a,b)=>a.d-b.d)[0];
    }
    function spawnCheck(x,z,name){
      const ref=nearest(x,z,name);
      const pos=roadSpawn(name||null,x,z);
      const dir=ref.s.l.oneway===-1?-1:1,dx=ref.s.dx*dir,dz=ref.s.dz*dir;
      const lateral=(pos[0]-ref.x)*(-dz)+(pos[1]-ref.z)*dx;
      const dot=Math.sin(pos[2])*dx+Math.cos(pos[2])*dz;
      const expected=ref.s.l.oneway?0:ref.s.l.w/4;
      c.teleportActiveTo(pos[0],pos[1],pos[2]);
      const actual=state(),displacement=Math.hypot(actual.x-pos[0],actual.z-pos[1]);
      return {way:ref.s.l.way,name:ref.s.l.name||null,oneway:ref.s.l.oneway,road_width_m:ref.s.l.w,requested:[x,z],spawn:pos.slice(0,3),actual,lateral_m:lateral,expected_lateral_m:expected,heading_dot:dot,displacement_m:displacement,
        pass:Math.abs(lateral-expected)<.05&&dot>.999&&displacement<.75&&inside(actual.x,actual.z)};
    }
    const spawn=spawnCheck(0,0,null);
    const paint=scene.getObjectByName('RoadMarkings');
    if(!paint?.userData?.trafficMarks||!paint.geometry.index)throw Error('Missing real paint mesh instrumentation');
    const marks=paint.userData.trafficMarks;
    const idx=paint.geometry.index.array,positions=paint.geometry.attributes.position.array;
    function offsets(mark){
      let lo=Infinity,hi=-Infinity;
      for(let i=mark.first;i<mark.first+mark.count;i++){
        const v=idx[i]*3,e=mark.edge;
        const d=(positions[v]-e.x0)*e.rx+(positions[v+2]-e.z0)*e.rz;
        lo=Math.min(lo,d);hi=Math.max(hi,d);
      }
      return {min:lo,max:hi};
    }
    const stops=marks.filter(m=>m.kind==='stop'&&m.edge.shared&&inside(...m.edge.to));
    const bars=stops.map(m=>({edge:m.edge,s:m.s,requested:[m.o0,m.o1],triangles:m.count/3,color:m.color,measured:offsets(m),
      pass:m.count>0&&m.count%3===0&&m.color===0xe6e2d6&&m.o0>=-.001&&m.o1>m.o0&&m.o1<=m.edge.half&&offsets(m).min>=-.05&&offsets(m).max<=m.edge.half+.05}));
    const marking={mesh_triangles:idx.length/3,right_stop_bars:bars,pass:bars.length>0&&bars.every(b=>b.pass)};
    const related=(m,e)=>same(m.edge.from,[e.from.x,e.from.z])&&same(m.edge.to,[e.to.x,e.to.z]);
    const centreLine=e=>marks.filter(m=>m.kind==='longitudinal'&&m.count>0&&Math.abs(m.offset)<.2&&(related(m,e)||same(m.edge.from,[e.to.x,e.to.z])&&same(m.edge.to,[e.from.x,e.from.z])));
    const at=(e,lane,s)=>({x:e.sx+e.dx*s+e.rx*e.lanes[lane],z:e.sz+e.dz*s+e.rz*e.lanes[lane]});
    const rawJunctions=RG.nodes.map((n,i)=>({x:n.x,z:n.z,ways:[...new Set(RG.links.filter(l=>l.a===i||l.b===i).map(l=>l.way))],degree:RG.links.filter(l=>l.a===i||l.b===i).length})).filter(n=>n.degree>=3&&n.ways.length>=2);
    const alternatives=[];
    for(const e of network.edges){
      if(e.centred!==false||e.divided||e.len<16||e.to.shape||e.from.lift>.05||e.to.lift>.05)continue;
      const raw=rawJunctions.map(n=>({n,d:distance(n,e.to)})).sort((a,b)=>a.d-b.d)[0];
      if(!raw||raw.d>3||!inside(e.to.x,e.to.z))continue;
      const stop=bars.filter(m=>m.edge.id===e.id);
      if(!stop.length||!centreLine(e).length)continue;
      for(const m of e.moves){
        const f=m.to;
        if(f.centred!==false||f.divided||f.len<16||f.to.lift>.05)continue;
        for(let i=0;i<e.lanes.length;i++){
          const j=m.out[i];if(j<0||e.lanes[i]<=.2||f.lanes[j]<=.2)continue;
          const curve=network.connector(e,i,f,j);
          if(curve.len<1||curve.len>35||curve.curv>.20)continue;
          const points=[at(e,i,e.len-13),at(e,i,e.len)];
          for(let s=.5;s<curve.len;s+=.5){const q=network.curvePoint(curve,s,{});points.push({x:q.x,z:q.z});}
          points.push(at(f,j,0),at(f,j,13));
          if(points.some(q=>!inside(q.x,q.z)))continue;
          alternatives.push({e,f,i,j,curve,points,raw:raw.n,turn:m.turn,score:curve.curv+(m.turn==='S'?0:.05),stop,lines:centreLine(e)});
        }
      }
    }
    alternatives.sort((a,b)=>a.score-b.score||a.e.id-b.e.id||a.f.id-b.f.id||a.i-b.i);
    const chosen=alternatives[0];
    function edgeRecord(e,lane){return {id:e.id,from:[e.from.x,e.from.z],to:[e.to.x,e.to.z],x0:e.x0,z0:e.z0,rx:e.rx,rz:e.rz,half:e.half,lane_offset:e.lanes[lane]};}
    // Actual one-way links, inside the playable area. Pick a straight interior
    // section with asphalt support, not a point on a synthetic ring.
    const oneCandidates=segments.filter(s=>s.l.oneway&&s.len>=10&&inside(s.a.x,s.a.z)&&inside(s.b.x,s.b.z))
      .map(s=>{
        const d=s.l.oneway===-1?-1:1,start=d===1?s.a:s.b,dx=d*s.dx,dz=d*s.dz;
        const a={x:start.x+dx*2,z:start.z+dz*2},end={x:start.x+dx*(s.len-2),z:start.z+dz*(s.len-2)};
        const road=Array.from({length:5},(_,i)=>pavementLift(a.x+(end.x-a.x)*i/4,a.z+(end.z-a.z)*i/4));
        return {s,a,end,dx,dz,road};
      }).filter(v=>v.road.every(y=>Math.abs(y-ROAD_Y)<.001)).sort((a,b)=>b.s.len-a.s.len||a.s.l.way-b.s.l.way);
    const one=oneCandidates[0];
    const complex=GEO.roads.filter(r=>[657862468,1245835693,303572277,303572242,1473693891,1473693893,1473693896,303572291,1479346973].includes(r.id));
    const xy=complex.flatMap(r=>Array.from({length:r.pts.length/2},(_,i)=>[r.pts[2*i],r.pts[2*i+1]]));
    const ring=xy.length?{ways:complex.map(r=>({id:r.id,name:r.name,oneway:r.oneway,roundabout:!!r.roundabout})),x:xy.reduce((s,p)=>s+p[0],0)/xy.length,z:xy.reduce((s,p)=>s+p[1],0)/xy.length,min_playable_margin_m:Math.min(...xy.map(p=>margin(...p))),controller_edge_margin_m:30}:null;
    p.test={chosen,one,spawnCheck,inside,state,heightAt,pavementLift,ROAD_Y,edgeRecord,clamp};
    return {terrain:{source:T.source,kind:T.kind,vertices:T.vertices.length/3,flat:GEO.frame.flatTerrain},spawn,marking,intersection:chosen?{real_osm_node:chosen.raw,turn:chosen.turn,from:edgeRecord(chosen.e,chosen.i),to:edgeRecord(chosen.f,chosen.j),centre_lines:chosen.lines.map(m=>({offset_m:m.offset,triangles:m.count/3,color:m.color})),alternatives:alternatives.length}:null,oneway:one?{way:one.s.l.way,name:one.s.l.name||null,oneway:one.s.l.oneway,from:one.a,to:one.end,length_m:distance(one.a,one.end)}:null,complex:ring};
  });
  Object.assign(report,setup);save();
  await capture('spawn-top-down',setup.spawn.actual.x,setup.spawn.actual.z,45);
  if(setup.complex){
    await capture('vim-real-oneway-complex-not-confirmed-roundabout',setup.complex.x,setup.complex.z,95);
    report.roundabout.nearby_real_complex=setup.complex;
    if(setup.complex.min_playable_margin_m<setup.complex.controller_edge_margin_m && tags.length===0){
      report.roundabout.status='not_applicable_in_pilot_bbox';
      report.roundabout.reason='Known VIM/Humberto Delgado/São Pedro complex intersects controller boundary; full ring cannot be validated in this pinned extract. Follow-up #35.';
    }
    save();
  }
  // Define once inside the live browser. Use the exact upstream controller.
  await page.evaluate(()=>{
    const {controllers:c,trafficPreview:p}=window.mapslop;
    const t=p.test,e=c.getActiveEntity();
    const angle=(a,b)=>Math.atan2(Math.sin(a-b),Math.cos(a-b));
    p.runDrive=(points,sections,spawn=null)=>{
      const route=[];
      for(const q of points){
        const prev=route.at(-1),d=prev?Math.hypot(q.x-prev.x,q.z-prev.z):0;
        if(prev&&d<.001)continue;
        route.push({...q,s:prev?prev.s+d:0});
      }
      const total=route.at(-1).s;
      const at=s=>{
        s=t.clamp(s,0,total);let i=0;
        while(i<route.length-2&&route[i+1].s<s)i++;
        const a=route[i],b=route[i+1],k=(s-a.s)/(b.s-a.s);
        return {x:a.x+(b.x-a.x)*k,z:a.z+(b.z-a.z)*k};
      };
      const project=(x,z,progress)=>{
        let best={d:Infinity,s:progress};
        for(let i=0;i+1<route.length;i++){
          const a=route[i],b=route[i+1];if(b.s<progress-5||a.s>progress+10)continue;
          const dx=b.x-a.x,dz=b.z-a.z,k=t.clamp(((x-a.x)*dx+(z-a.z)*dz)/(dx*dx+dz*dz),0,1);
          const d=Math.hypot(x-a.x-k*dx,z-a.z-k*dz);
          if(d<best.d)best={d,s:a.s+(b.s-a.s)*k};
        }
        return best;
      };
      const start=route[0],next=at(Math.min(1,total));
      const h=Math.atan2(next.x-start.x,next.z-start.z);
      if(!spawn)c.teleportActiveTo(start.x,start.z,h);
      const actual=t.state(),spawn_error=Math.hypot(actual.x-start.x,actual.z-start.z);
      let progress=0,collisions=0,maxCross=0,maxContact=0,roadFrames=0,frames=0,reason='timeout';
      const samples=[],checks=sections.map(s=>({label:s.label,min_offset:Infinity,max_offset:-Infinity,samples:0,wrong_side:0}));
      c.setCollisionListener(()=>collisions++);
      try{
        if(spawn_error>.75||Math.abs(angle(actual.heading,h))>.15)reason='spawn mismatch';
        else for(let i=0;i<60*35;i++){
          const pos=e.position,q=project(pos.x,pos.z,progress);progress=Math.max(progress,q.s);
          if(!Number.isFinite(q.d)||q.d>1.25){reason='left planned lane';break;}
          if(progress>=total-.6){reason='complete';break;}
          const look=3.5+Math.max(0,e.speed)*.25,target=at(progress+look);
          const delta=angle(Math.atan2(target.x-pos.x,target.z-pos.z),e.heading);
          const steer=t.clamp(Math.atan2(2*2.76*Math.sin(delta),look)/.60,-1,1);
          c.setTouchInput('left',Math.max(0,steer));c.setTouchInput('right',Math.max(0,-steer));
          const speed=2.8;
          c.setTouchInput('forward',t.clamp((speed-e.speed)/1.8,0,1));
          c.setTouchInput('backward',t.clamp((e.speed-speed-.15)/1.2,0,1));
          c.update(1/60,(i+1)/60);
          const v=t.state(),p0=project(v.x,v.z,progress);
          maxCross=Math.max(maxCross,p0.d);maxContact=Math.max(maxContact,Math.abs(v.y-t.heightAt(v.x,v.z)));
          frames++;if(Math.abs(t.pavementLift(v.x,v.z)-t.ROAD_Y)<.001)roadFrames++;
          for(let k=0;k<sections.length;k++){
            const s=sections[k];if(p0.s<s.from||p0.s>s.to)continue;
            const off=(v.x-s.x0)*s.rx+(v.z-s.z0)*s.rz,row=checks[k];
            row.min_offset=Math.min(row.min_offset,off);row.max_offset=Math.max(row.max_offset,off);row.samples++;
            if(off<s.min||off>s.max)row.wrong_side++;
          }
          if(i%15===0)samples.push({...v,station_m:p0.s,cross_track_m:p0.d});
          if(!t.inside(v.x,v.z)||maxContact>.5||collisions){reason='collision/contact/extent';break;}
        }
      }finally{c.resetInput();c.setCollisionListener(null);}
      const end=t.state();
      const pass=reason==='complete'&&collisions===0&&maxCross<=1.25&&maxContact<=.5&&frames>=30&&roadFrames/frames>=.95&&checks.every(s=>s.samples>=10&&s.wrong_side===0);
      return {pass,reason,length_m:total,progress_m:progress,spawn_error_m:spawn_error,max_cross_track_m:maxCross,max_contact_m:maxContact,collisions,frames,asphalt_fraction:frames?roadFrames/frames:0,sections:checks.map(s=>({...s,min_offset:Number.isFinite(s.min_offset)?s.min_offset:null,max_offset:Number.isFinite(s.max_offset)?s.max_offset:null})),start:actual,end,samples};
    };
  });
  if(setup.intersection){
    const j=await page.evaluate(()=>{
      const p=window.mapslop.trafficPreview,q=p.test.chosen;
      const sections=[{label:'approach_right',from:1,to:10,x0:q.e.x0,z0:q.e.z0,rx:q.e.rx,rz:q.e.rz,min:.15,max:q.e.half-.65},
        {label:'exit_right',from:13+q.curve.len+2,to:13+q.curve.len+11,x0:q.f.x0,z0:q.f.z0,rx:q.f.rx,rz:q.f.rz,min:.15,max:q.f.half-.65}];
      return p.runDrive(q.points,sections);
    });
    report.intersection.drive=j;save();
    await capture('junction-real-markings-and-car',setup.intersection.real_osm_node.x,setup.intersection.real_osm_node.z,60);
  }
  if(setup.oneway){
    const o=await page.evaluate(()=>{
      const p=window.mapslop.trafficPreview,q=p.test.one;
      const spawn=p.test.spawnCheck(q.a.x,q.a.z,q.s.l.name||null);
      const drive=p.runDrive([q.a,q.end],[{label:'oneway_corridor',from:1,to:Math.hypot(q.end.x-q.a.x,q.end.z-q.a.z)-1,x0:q.a.x,z0:q.a.z,rx:-q.dz,rz:q.dx,min:-q.s.l.w/2+.65,max:q.s.l.w/2-.65}],true);
      const dot=Math.sin(drive.end.heading)*q.dx+Math.cos(drive.end.heading)*q.dz;
      return {spawn,drive,heading_dot:dot,pass:spawn.pass&&spawn.way===q.s.l.way&&drive.pass&&dot>.8};
    });
    report.oneway.validation=o;save();
    await capture('real-oneway-driven',o.drive.end.x,o.drive.end.z,45);
  }
  report.available_cases_pass=setup.terrain.source==='DGT MDT 0.5 m'&&setup.terrain.kind==='tin'&&setup.terrain.vertices===126528&&!setup.terrain.flat&&report.hud?.pass===true&&setup.spawn.pass&&setup.marking.pass&&report.intersection?.drive?.pass===true&&report.oneway?.validation?.pass===true&&report.errors.length===0&&report.console_errors.length===0&&report.failed_requests.every(r=>r.url.endsWith('/favicon.ico'));
  // Explicitly partial: the pilot has no tagged real roundabout.
  // A future source update requires a separate real-ring route and review.
  if(tags.length)report.roundabout.reason='Tagged feature exists in source but no verified real ring drive; manual inspection required';
  save();
  console.log('TRAFFIC_RESULT',JSON.stringify({available_cases_pass:report.available_cases_pass,roundabout:report.roundabout,intersection:report.intersection?.drive?.pass,oneway:report.oneway?.validation?.pass,marking:report.marking?.pass}));
}catch(error){report.errors.push(String(error));save();try{await page.screenshot({path:path.join(root,'failure.png'),timeout:15000})}catch{};console.error(error);process.exitCode=1}
finally{await browser.close();save()}
