// Browser-side route test. Real controller, collision and terrain modules.
// Accelerated deterministic physics (1/60 s); the short browser smoke separately
// exercises live rendering, keyboard and multitouch. No position writes during drive.
export async function driveTerrainRoute({reference=null,minGrade=0.02}={}){
  const {heightAt}=await import(new URL('js/terrain.js',location.href).href);
  const {GEO,controllers:c}=window.mapslop;
  // Actual OSM road graph link endpoints, counted across distinct ways.
  const junctions=[]; const seen=new Map();
  for(const road of GEO.roads){for(let i=0;i<road.pts.length;i+=2){const x=road.pts[i],z=road.pts[i+1],key=x.toFixed(1)+','+z.toFixed(1);if(!seen.has(key))seen.set(key,{x,z,ways:new Set()});seen.get(key).ways.add(road.id);}}
  for(const p of seen.values())if(p.ways.size>1)junctions.push(p);
  const e=c.getActiveEntity();
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const angle=(a,b)=>Math.atan2(Math.sin(a-b),Math.cos(a-b));
  const heading=(a,b)=>Math.atan2(b[0]-a[0],b[1]-a[1]);
  const distance=(a,b)=>Math.hypot(b[0]-a[0],b[1]-a[1]);
  function polyline(pts){
    const a=[];
    for(let i=0;i<pts.length;i+=2){
      const v=[pts[i],pts[i+1],0];
      if(a.length){
        const d=distance(a.at(-1),v);
        if(d<1e-5)continue;
        v[2]=a.at(-1)[2]+d;
      }
      a.push(v);
    }
    return a;
  }
  function at(a,s){
    s=clamp(s,0,a.at(-1)[2]);
    let i=0;while(i<a.length-2&&a[i+1][2]<s)i++;
    const p=a[i],q=a[i+1],f=(s-p[2])/(q[2]-p[2]);
    return [p[0]+f*(q[0]-p[0]),p[1]+f*(q[1]-p[1]),s];
  }
  function metrics(a){
    const y=a.map(p=>heightAt(p[0],p[1]));
    let grade=0,sharp=0,turn=0,lo=0,hi=0,prev=null;
    // 20 m grade and sustained heading change, within first 100 m.
    for(let i=0;i<=40;i++)grade=Math.max(grade,Math.abs(y[i+10]-y[i])/20);
    for(let i=0;i<=46;i+=2){
      const h=heading(a[i],a[i+4]);
      if(prev!==null){const d=angle(h,prev);turn+=d;sharp=Math.max(sharp,Math.abs(d));}
      lo=Math.min(lo,turn);hi=Math.max(hi,turn);prev=h;
    }
    return {grade,turnDegrees:(hi-lo)*180/Math.PI,sharpDegrees:sharp*180/Math.PI};
  }
  function choose(){
    const T=GEO.terrain;
    const X=T.x0+(T.nx-1)*T.cell,Z=T.z0+(T.nz-1)*T.cell;
    const eligible=new Set(GEO.roadGraph.links.filter(l=>!l.bridge&&!l.tunnel&&!l.layer).map(l=>l.way));
    const candidates=[];
    for(const r of GEO.roads){
      if(!eligible.has(r.id)||!r.name||r.bridge||r.tunnel||r.layer||r.oneway!==0||r.w<5.5||r.roundabout)continue;
      const p=polyline(r.pts);
      if(p.length<2||p.at(-1)[2]<128)continue;
      for(let s=4;s+124<=p.at(-1)[2];s+=6){
        const a=Array.from({length:61},(_,i)=>at(p,s+2*i));
        if(a.some(v=>v[0]<T.x0+40||v[0]>X-40||v[1]<T.z0+40||v[1]>Z-40))continue;
        a.forEach((v,i)=>v[2]=2*i);
        const m=metrics(a);
        if(m.grade<minGrade||m.turnDegrees<20||m.sharpDegrees>35)continue;
        // Prefer wide, gentle, sustained bends and meaningful but not extreme slopes.
        const score=r.w*2+Math.min(m.turnDegrees,45)*0.08-m.sharpDegrees*0.15-Math.abs(m.grade-0.055)*40;
        candidates.push({way:r.id,name:r.name,width:r.w,points:a,score,...m});
      }
    }
    candidates.sort((a,b)=>b.score-a.score||a.way-b.way);
    return candidates.slice(0,5);
  }
  function project(a,x,z,progress){
    let best={s:progress,d:Infinity};
    for(let i=0;i<a.length-1;i++){
      const p=a[i],q=a[i+1];
      if(q[2]<progress-8||p[2]>progress+20)continue;
      const dx=q[0]-p[0],dz=q[1]-p[1];
      const t=clamp(((x-p[0])*dx+(z-p[1])*dz)/(dx*dx+dz*dz),0,1);
      const d=Math.hypot(x-(p[0]+dx*t),z-(p[1]+dz*t));
      if(d<best.d)best={d,s:p[2]+t*(q[2]-p[2])};
    }
    return best;
  }
  function attempt(route){
    const a=route.points,m=metrics(a);
    const h0=heading(a[0],a[2]);
    c.teleportActiveTo(a[0][0],a[0][1],h0);
    if(distance(a[0],[e.position.x,e.position.z])>1.5)
      return {route,success:false,reason:'Spawn not clear',distance_m:0};
    let distanceM=0,progress=0,maxCross=0,maxGround=0,maxSurface=0,sumGround=0,samples=0;
    let last=[e.position.x,e.position.z],prevHeading=e.heading,headingAccum=0,hmin=0,hmax=0;
    let minY=Infinity,maxY=-Infinity,collisions=0,reason='Timeout';
    const trace=[],vertical=[],rollStraight=[],bodyRoll=[],wheelDelta=[],dt=1/60;
    c.setCollisionListener(()=>collisions++);
    try {
      for(let i=0;i<60*55;i++){
        const p=e.position;
        const q=project(a,p.x,p.z,progress);
        if(!Number.isFinite(q.d)){reason='Lost route';break;}
        progress=Math.max(progress,q.s);maxCross=Math.max(maxCross,q.d);
        if(q.d>route.width/2-0.35){reason='Left road corridor';break;}
        const look=clamp(4+Math.max(0,e.speed)*0.38,4,7);
        const target=at(a,progress+look);
        const delta=angle(Math.atan2(target[0]-p.x,target[1]-p.z),e.heading);
        const steer=clamp(Math.atan2(2*2.76*Math.sin(delta),look)/0.60,-1,1);
        const targetSpeed=5.5;
        c.setTouchInput('left',Math.max(0,steer));c.setTouchInput('right',Math.max(0,-steer));
        c.setTouchInput('forward',clamp((targetSpeed-e.speed)/1.8,0,1));
        c.setTouchInput('backward',clamp((e.speed-targetSpeed-0.4)/1.8,0,1));
        c.update(dt,(i+1)*dt);
        const pos=e.position;
        const raw=heightAt(pos.x,pos.z),surface=c.getGroundHeight(pos.x,pos.z,'car',pos.y);
        const ge=Math.abs(pos.y-raw),se=Math.abs(pos.y-surface);
        if(![pos.x,pos.y,pos.z,ge,se].every(Number.isFinite)){reason='Nonfinite physics';break;}
        distanceM+=distance(last,[pos.x,pos.z]);last=[pos.x,pos.z];
        maxGround=Math.max(maxGround,ge);maxSurface=Math.max(maxSurface,se);sumGround+=ge;samples++;
        minY=Math.min(minY,raw);maxY=Math.max(maxY,raw);
        const station=project(a,pos.x,pos.z,progress).s;
        const near=junctions.reduce((m,j)=>{const d=Math.hypot(pos.x-j.x,pos.z-j.z);return d<m?d:m;},Infinity);
        vertical.push({ground:surface,terrain:raw,car:pos.y,speed:e.speed,station_m:station,x_m:pos.x,z_m:pos.z,way:route.way,junction_distance_m:Number.isFinite(near)?near:null,step:i});
        if(Math.abs(steer)<0.04&&Math.abs(e.speed)>3){
          const roll=(e.mesh.rotation.z||0)+(e.chassisPivot?.rotation.z||0);
          bodyRoll.push(Math.abs(roll*180/Math.PI));
          // The model's actual four wheel offsets, yaw transformed onto the common collision surface.
          const wheels=e.wheels.map(w=>{const v=w.steerPivot.position,si=Math.sin(e.heading),co=Math.cos(e.heading);
            const x=pos.x+co*v.x+si*v.z,z=pos.z-si*v.x+co*v.z;
            return {side:Math.sign(v.x),axle:Math.sign(v.z),offset:v.x,y:c.getGroundHeight(x,z,'car',pos.y)};});
          for(const axle of [-1,1]){
            const left=wheels.find(w=>w.axle===axle&&w.side<0),right=wheels.find(w=>w.axle===axle&&w.side>0);
            if(!left||!right)continue;
            const dy=right.y-left.y,track=right.offset-left.offset;
            if(Number.isFinite(dy)&&track>0){wheelDelta.push(Math.abs(dy));rollStraight.push(Math.abs(Math.atan2(dy,track)*180/Math.PI));}
          }
        }
        headingAccum+=angle(e.heading,prevHeading);prevHeading=e.heading;
        hmin=Math.min(hmin,headingAccum);hmax=Math.max(hmax,headingAccum);
        if(i%30===0)trace.push({distance_m:distanceM,progress_m:progress,ground_m:ge,surface_m:se,terrain_y_m:raw});
        if(ge>0.5||se>0.5){reason='Contact exceeded 0.5 m';break;}
        if(progress>=104&&distanceM>=100){reason='Reached target';break;}
      }
    }finally{c.resetInput();c.setCollisionListener(null);}
    const headingRange=(hmax-hmin)*180/Math.PI;
    function acceleration(key,k){
      let max=0,count=0;const peaks=[];
      for(let i=k;i<vertical.length-k;i++){
        if(vertical[i].speed<3)continue;
        const a=Math.abs(vertical[i+k][key]-2*vertical[i][key]+vertical[i-k][key])/(k*dt)**2;
        max=Math.max(max,a);count++;
        peaks.push({...vertical[i],acceleration_m_s2:a,previous_y_m:vertical[i-k][key],next_y_m:vertical[i+k][key],sample_interval_s:k*dt});
      }
      peaks.sort((a,b)=>b.acceleration_m_s2-a.acceleration_m_s2);
      const top=[];for(const p of peaks){if(top.every(q=>Math.abs(p.station_m-q.station_m)>.5))top.push(p);if(top.length===10)break;}
      return {max_m_s2:count?max:null,samples:count,peaks:top};
    }
    const verticalMetrics={surface_raw:acceleration('ground',1),surface_window_0_2s:acceleration('ground',6),
      vehicle_raw:acceleration('car',1),vehicle_window_0_2s:acceleration('car',6),
      terrain_raw:acceleration('terrain',1),terrain_window_0_2s:acceleration('terrain',6),
      straight_roll_max_degrees:rollStraight.length?Math.max(...rollStraight):null,straight_roll_samples:rollStraight.length,
      straight_wheel_height_delta_max_m:wheelDelta.length?Math.max(...wheelDelta):null,
      chassis_dynamic_roll_max_degrees:bodyRoll.length?Math.max(...bodyRoll):null,roll_method:'left/right collision-surface height at actual axle offsets; front and rear, max'};
    const result={route,reason,distance_m:distanceM,progress_m:progress,sample_count:samples,
      contact_max_m:maxGround,contact_mean_m:samples?sumGround/samples:null,surface_contact_max_m:maxSurface,
      max_cross_track_m:maxCross,road_grade_20m:m.grade,road_turn_degrees:m.turnDegrees,
      driven_heading_range_degrees:headingRange,elevation_range_m:samples?maxY-minY:null,collisions,trace,
      vertical_metrics:verticalMetrics,simulation_step_s:dt,method:'live browser controller, fixed-step physics (rendered smoke separate)'};
    result.success=reason==='Reached target'&&distanceM>=100&&progress>=100&&samples>=100&&
      headingRange>=15&&m.grade>=minGrade&&maxGround<=0.5&&maxSurface<=0.5&&collisions===0;
    return result;
  }
  if(e.type!=='car')throw Error('Long route requires car');
  const candidates=reference?[reference]:choose();
  if(!candidates.length)return {success:false,reason:'No interior sloped curved road candidate',attempts:[]};
  const attempts=[];
  for(const route of candidates){
    const r=attempt(route);
    attempts.push(r);
    if(r.success)return {...r,attempts:attempts.map(({trace,route,...m})=>({way:route.way,name:route.name,...m}))};
  }
  return {...attempts.at(-1),attempts:attempts.map(({trace,route,...m})=>({way:route.way,name:route.name,...m}))};
}
