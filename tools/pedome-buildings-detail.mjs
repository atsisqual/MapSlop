// Private opt-in building preview. Canonical GEO remains unchanged on Pages.
import * as THREE from 'three/webgpu';
import { GEO } from './nairobi-geodata.js';
import { heightAt, tin } from './terrain.js';

const ringPoints=r=>Array.from({length:r.length/2},(_,i)=>new THREE.Vector2(r[2*i],r[2*i+1]));
function inside(r,x,z){
  let v=false;
  for(let i=0,j=r.length-2;i<r.length;j=i,i+=2){
    if((r[i+1]>z)!==(r[j+1]>z)&&x<(r[j]-r[i])*(z-r[i+1])/(r[j+1]-r[i+1])+r[i])v=!v;
  }
  return v;
}
const hash=id=>{let v=2166136261;for(const c of String(id)){v=Math.imul(v^c.charCodeAt(0),16777619);}return (v>>>0)/4294967296;};
const mat=(color)=>new THREE.MeshStandardMaterial({color,roughness:.88,side:THREE.DoubleSide});
const buckets=new Map();
function tri(m,a,b,c){
  if(!buckets.has(m))buckets.set(m,[]);
  const n=new THREE.Vector3(...b).sub(new THREE.Vector3(...a)).cross(new THREE.Vector3(...c).sub(new THREE.Vector3(...a)));
  if(n.lengthSq()>1e-10)buckets.get(m).push(...a,...b,...c);
}
function quad(m,a,b,c,d){tri(m,a,b,c);tri(m,a,c,d);}
function clipAbove(p,y){
  const out=[];
  for(let i=0;i<p.length;i++){
    const a=p[i],b=p[(i+1)%p.length],ia=a[1]>=y,ib=b[1]>=y;
    if(ia)out.push(a);
    if(ia!==ib){const t=(y-a[1])/(b[1]-a[1]);out.push([a[0]+t*(b[0]-a[0]),y,a[2]+t*(b[2]-a[2])]);}
  }
  return out;
}
function bounds(b){
  let min=Infinity,max=-Infinity;
  const add=(x,z)=>{const y=heightAt(x,z);min=Math.min(min,y);max=Math.max(max,y);};
  const rings=[b.ring,...(b.holes||[])];
  for(const r of rings)for(let i=0;i<r.length;i+=2){
    const j=(i+2)%r.length,a=[r[i],r[i+1]],q=[r[j],r[j+1]];
    const n=Math.max(1,Math.ceil(Math.hypot(q[0]-a[0],q[1]-a[1])/.5));
    for(let k=0;k<=n;k++)add(a[0]+(q[0]-a[0])*k/n,a[1]+(q[1]-a[1])*k/n);
    if(tin)for(const t of tin.segmentBreaks(...a,...q))add(a[0]+(q[0]-a[0])*t,a[1]+(q[1]-a[1])*t);
  }
  const xs=b.ring.filter((_,i)=>i%2===0),zs=b.ring.filter((_,i)=>i%2===1);
  if(tin)for(const i of tin.faces(Math.min(...xs),Math.min(...zs),Math.max(...xs),Math.max(...zs))){
    const r=tin.triangle(i);
    for(let j=0;j<6;j+=2)if(inside(b.ring,r[j],r[j+1])&&!(b.holes||[]).some(h=>inside(h,r[j],r[j+1])))add(r[j],r[j+1]);
  }
  return {min,max};
}
export const detailBases=new Map();
function wallRing(b,low,high,material){
  for(const r of [b.ring,...(b.holes||[])])for(let i=0;i<r.length;i+=2){
    const j=(i+2)%r.length,x=r[i],z=r[i+1],u=r[j],v=r[j+1];
    quad(material,[x,low,z],[u,low,v],[u,high,v],[x,high,z]);
  }
}
function flatRoof(b,y,m){
  const p=ringPoints(b.ring),holes=(b.holes||[]).map(ringPoints),all=p.concat(...holes);
  for(const ids of THREE.ShapeUtils.triangulateShape(p,holes))tri(m,...ids.map(i=>[all[i].x,y,all[i].y]));
}
function simpleRoof(b,base,top,roofMat,wallMat){
  const p=ringPoints(b.ring),shape=String(b.roof||'').toLowerCase();
  if(shape==='flat'||b.use==='industrial'||b.use==='warehouse'||b.part||b.minH||p.length!==4||b.holes?.length){
    wallRing(b,base,top,wallMat);flatRoof(b,top,roofMat);return {eave:top,shape:'flat_safe'};
  }
  const d=p.map((q,i)=>q.distanceTo(p[(i+1)%4]));
  const i=d[0]+d[2]>=d[1]+d[3]?0:1;
  const q=Array.from({length:4},(_,j)=>p[(i+j)%4]);
  // Only convex quads are supported; preserve complex footprint topology with flat fallback.
  const cross=q.map((v,j)=>{const a=q[(j+1)%4].clone().sub(v),c=q[(j+2)%4].clone().sub(q[(j+1)%4]);return a.x*c.y-a.y*c.x;});
  if(!(cross.every(v=>v>0)||cross.every(v=>v<0))){wallRing(b,base,top,wallMat);flatRoof(b,top,roofMat);return {eave:top,shape:'flat_safe'};}
  const long=(d[i]+d[(i+2)%4])/2,wide=(d[(i+1)%4]+d[(i+3)%4])/2;
  const hip=shape==='hipped'||shape!=='gabled'&&long/Math.max(wide,.1)<1.5;
  const rise=Math.min(2.5,Math.max(.4,wide*.23),Math.max(.3,(top-base)*.3));
  const eave=top-rise;
  if(eave-base<1.0){wallRing(b,base,top,wallMat);flatRoof(b,top,roofMat);return {eave:top,shape:'flat_safe'};}
  wallRing(b,base,eave,wallMat);
  const a=q[0].clone().add(q[3]).multiplyScalar(.5),c=q[1].clone().add(q[2]).multiplyScalar(.5);
  const f=hip?Math.min(.45,wide/(2*Math.max(long,.1))):0;
  const u=a.clone().lerp(c,f),v=c.clone().lerp(a,f);
  const at=(p,y)=>[p.x,y,p.y],Q=q.map(p=>at(p,eave)),U=at(u,top),V=at(v,top);
  quad(roofMat,Q[0],Q[1],V,U);quad(roofMat,Q[2],Q[3],U,V);
  tri(hip?roofMat:wallMat,Q[3],Q[0],U);tri(hip?roofMat:wallMat,Q[1],Q[2],V);
  return {eave,shape:hip?'hipped':'gabled'};
}
function instances(group,items,geometry,material,name){
  if(!items.length)return;
  const mesh=new THREE.InstancedMesh(geometry,material,items.length),o=new THREE.Object3D();
  items.forEach((item,i)=>{o.position.set(...item.p);o.scale.set(...item.s);o.rotation.set(0,item.yaw,0);o.updateMatrix();mesh.setMatrixAt(i,o.matrix);});
  mesh.instanceMatrix.needsUpdate=true;mesh.name=name;group.add(mesh);
}
export function buildDetailedBuildings(){
  buckets.clear();detailBases.clear();
  const group=new THREE.Group();
  const facade=[0xf4eedc,0xe9e4d6,0xf7f5ee,0xdccdb4].map(mat),roof=[0xa94a32,0xb95739,0x984732].map(mat),stone=mat(0x8d8980);
  const windows=[],doors=[],rows=[];
  const sample=GEO.roofPreview||{};
  for(const b of GEO.buildings){
    const {min,max}=bounds(b),r=hash(b.id),fm=facade[Math.floor(r*facade.length)],rm=roof[Math.floor(hash(String(b.id)+'r')*roof.length)];
    detailBases.set(b,min);
    let top=min+b.h,base=Math.max(min,max),eave=top,policy='procedural_fallback',reason=null;
    const src=sample[String(b.id)];
    const elevated=!!(b.minH||b.part);
    if(elevated)base=min+(b.minH||0);
    else if(top-base<1.6)top=base+1.6;
    if(!elevated&&base>min+.01)wallRing(b,min,base,stone);
    if(src?.policy==='roofer_lod22_candidate'&&!elevated){
      // Verify correspondence to OSM footprint and the approved TIN in the actual runtime frame.
      const xs=b.ring.filter((_,i)=>i%2===0),zs=b.ring.filter((_,i)=>i%2===1);
      const coords=src.roof.concat(src.walls);
      let ok=src.roof_min_y>base+1.0&&src.roof_max_y>max+1&&src.wall_min_y>=min-1&&src.wall_min_y<=base+.15;
      for(let i=0;i<coords.length;i+=3)if(coords[i]<Math.min(...xs)-1.5||coords[i]>Math.max(...xs)+1.5||coords[i+2]<Math.min(...zs)-1.5||coords[i+2]>Math.max(...zs)+1.5)ok=false;
      if(ok){
        for(let i=0;i<src.roof.length;i+=9)tri(rm,src.roof.slice(i,i+3),src.roof.slice(i+3,i+6),src.roof.slice(i+6,i+9));
        for(let i=0;i<src.walls.length;i+=9){const q=clipAbove([src.walls.slice(i,i+3),src.walls.slice(i+3,i+6),src.walls.slice(i+6,i+9)],base);for(let j=1;j<q.length-1;j++)tri(fm,q[0],q[j],q[j+1]);}
        top=src.roof_max_y;eave=src.roof_min_y;policy='roofer_lod22';
        if(src.wall_min_y>base+.02)wallRing(b,base,src.wall_min_y,stone);
      }else reason='measured_geometry_frame_or_ground_mismatch';
    }
    if(policy!=='roofer_lod22'){
      const result=simpleRoof(b,base,top,rm,fm);eave=result.eave;
      reason=reason||src?.reason||'no_measured_roof';
      policy=result.shape;
    }
    // Reuse simple footprint colliders; max height is the ridge (conservative roof collision).
    b.h=top-min;
    if(!elevated&&policy!=='roofer_lod22'){
      let door=false;
      for(let i=0;i<b.ring.length;i+=2){
        const j=(i+2)%b.ring.length,ax=b.ring[i],az=b.ring[i+1],bx=b.ring[j],bz=b.ring[j+1],dx=bx-ax,dz=bz-az,len=Math.hypot(dx,dz);
        if(len<2.2)continue;
        const nx=dz/len,nz=-dx/len,yaw=Math.atan2(nx,nz);
        const bays=Math.max(1,Math.floor(len/2.8)),floors=Math.max(1,Math.floor((eave-base)/2.9));
        for(let floor=0;floor<floors;floor++)for(let k=0;k<bays;k++){
          const t=(k+.5)/bays,py=base+floor*2.9+1.5;
          if(py+.55>eave-.1)continue;
          const p=[ax+dx*t+nx*.035,py,az+dz*t+nz*.035];
          if(!door&&floor===0&&k===0&&base+2.15<=eave){p[1]=base+1.05;doors.push({p,s:[.85,2.1,.08],yaw});door=true;}
          else windows.push({p,s:[.95,1.1,.065],yaw});
        }
      }
    }
    rows.push({osm_id:b.id,policy,reason,foundation_min_m:min,terrain_max_m:max,habitable_base_m:base,roof_top_m:top});
  }
  let shell=0;
  for(const [m,pos] of buckets){
    if(!pos.length)continue;
    const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));geo.computeVertexNormals();
    const mesh=new THREE.Mesh(geo,m);group.add(mesh);shell+=pos.length/9;
  }
  const box=new THREE.BoxGeometry(1,1,1);
  instances(group,windows,box,mat(0x3f4c50),'Portuguese windows');
  instances(group,doors,box,mat(0x6e4934),'Portuguese doors');
  const report={buildings:rows.length,measured:rows.filter(r=>r.policy==='roofer_lod22').length,
    shell_triangles:shell,window_instances:windows.length,door_instances:doors.length,
    all_triangles:shell+12*(windows.length+doors.length),building_draw_calls:group.children.length,rows};
  group.userData.buildingDetailReport=report;
  return group;
}
