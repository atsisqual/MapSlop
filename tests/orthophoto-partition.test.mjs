import assert from 'node:assert/strict';
import {partitionTin} from '../tools/orthophoto-partition.mjs';
const p=[0,0,0, 200,20,0, 0,10,100],n=[0,1,0,0,1,0,0,1,0];
const m={tile_m:128,cols:2,rows:1,gutter_m:2,world_extent:[0,0,200,100]};
const r=partitionTin(p,n,[0,2,1],m);
assert.equal(r.inputArea,10000);
assert.ok(Math.abs(r.outputArea-r.inputArea)<1e-8);
assert.equal(r.parts.length,2);
for(const [i,part] of r.parts.entries()){
 assert.ok(part.indices.length>0);
 for(let k=0;k<part.positions.length;k+=3){
  const [x,y,z]=part.positions.slice(k,k+3);
  assert.ok(Math.abs(y-.1*x-.1*z)<1e-8,'height on original plane');
  assert.ok(x>=i*128-1e-8&&x<=(i+1)*128+1e-8);
  assert.ok(Math.abs(part.uv[2*k/3]-(x-i*128+2)/132)<1e-8);
  assert.ok(Math.abs(part.uv[2*k/3+1]-(1-(z+2)/132))<1e-8);
  for(const px of [64,128,512]){
   const u=part.uv[2*k/3],v=part.uv[2*k/3+1],mpp=132/px;
   const cx=Math.min(px-1,Math.max(0,Math.floor(u*px))),cz=Math.min(px-1,Math.max(0,Math.floor((1-v)*px)));
   assert.ok(Math.hypot(i*128-2+(cx+.5)*mpp-x,-2+(cz+.5)*mpp-z)<=Math.SQRT2*mpp/2+1e-8);
  }
 }
}
console.log('ORTHO_PARTITION_TEST PASS');
