// Portugal: x east, z south. Right normal to (dx,dz) is (-dz,dx).
// Offsets measured along that normal; positive means right of travel.
export const ACROSS = 'L';
export function rightLanes(count,step){
  if(!Number.isInteger(count)||count<1||!(step>0))throw Error('Invalid lane dimensions');
  return Array.from({length:count},(_,i)=>(i+.5)*step);
}
export function rightOf(lanes){
  const step=lanes.length>1?lanes[1]-lanes[0]:3.3;
  return lanes.map(v=>v-lanes[0]+step/2);
}
export function stopBand(edge,hasOpposing){
  const kerb=edge.half-.1;
  const shared=hasOpposing||edge.divided||edge.centred===false;
  return [shared?Math.max(-kerb,edge.lanes[0]-1.8,0):-kerb,kerb];
}
export function spawnOffset(width,oneway){
  return oneway?0:width/4;
}
export function directedSpawn(x,z,dx,dz,width,oneway){
  const length=Math.hypot(dx,dz);
  if(!(length>0))throw Error('Invalid spawn direction');
  const dir=oneway===-1?-1:1;
  const fx=dir*dx/length,fz=dir*dz/length;
  const off=spawnOffset(width,oneway);
  return [x-fz*off,z+fx*off,Math.atan2(fx,fz),fz,-fx];
}
