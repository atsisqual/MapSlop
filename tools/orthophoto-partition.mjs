// Partition the existing TIN into exact tile polygons; never alter collision geometry.
// Each clip intersection interpolates y and normals on the original triangle.
function clip(poly,axis,bound,sign){
 const out=[];
 for(let i=0;i<poly.length;i++){
  const a=poly[i],b=poly[(i+1)%poly.length];
  const da=sign*(a[axis]-bound),db=sign*(b[axis]-bound);
  if(da>=0)out.push(a);
  if((da>=0)!==(db>=0)){
   const t=da/(da-db),v=a.map((x,k)=>x+(b[k]-x)*t);v[axis]=bound;out.push(v);
  }
 }
 return out;
}
export function partitionTin(positions,normals,indices,manifest){
 const {tile_m:s,cols,rows,gutter_m:g,world_extent:[x0,z0]}=manifest;
 const parts=Array.from({length:cols*rows},()=>({positions:[],normals:[],uv:[],indices:[],keys:new Map()}));
 const vertex=k=>[positions[k*3],positions[k*3+1],positions[k*3+2],normals[k*3],normals[k*3+1],normals[k*3+2]];
 const clamp=(i,n)=>Math.max(0,Math.min(n-1,i));
 const add=(part,v,x,z)=>{
  const key=v.slice(0,3).map(a=>Math.round(a*100000)).join(',');
  let n=part.keys.get(key);
  if(n!==undefined)return n;
  n=part.positions.length/3;part.keys.set(key,n);
  part.positions.push(...v.slice(0,3));part.normals.push(...v.slice(3));
  part.uv.push((v[0]-x+g)/(s+2*g),1-(v[2]-z+g)/(s+2*g));return n;
 };
 let inputArea=0,outputArea=0,triangles=0;
 const area=(a,b,c)=>Math.abs((b[0]-a[0])*(c[2]-a[2])-(b[2]-a[2])*(c[0]-a[0]))*.5;
 for(let n=0;n<indices.length;n+=3){
  const tri=[vertex(indices[n]),vertex(indices[n+1]),vertex(indices[n+2])];
  inputArea+=area(...tri);
  const xs=tri.map(v=>v[0]),zs=tri.map(v=>v[2]);
  const i0=clamp(Math.floor((Math.min(...xs)-x0)/s),cols),i1=clamp(Math.floor((Math.max(...xs)-x0)/s),cols);
  const j0=clamp(Math.floor((Math.min(...zs)-z0)/s),rows),j1=clamp(Math.floor((Math.max(...zs)-z0)/s),rows);
  for(let j=j0;j<=j1;j++)for(let i=i0;i<=i1;i++){
   const x=x0+i*s,z=z0+j*s,part=parts[j*cols+i];
   let poly=tri;
   for(const [axis,bound,sign] of [[0,x,1],[0,x+s,-1],[2,z,1],[2,z+s,-1]]){poly=clip(poly,axis,bound,sign);if(poly.length<3)break;}
   for(let k=1;k+1<poly.length;k++){
    const a=poly[0],b=poly[k],c=poly[k+1],ar=area(a,b,c);
    if(ar<1e-9)continue;
    const ids=[add(part,a,x,z),add(part,b,x,z),add(part,c,x,z)];
    if(new Set(ids).size<3)continue;
    part.indices.push(...ids);outputArea+=ar;triangles++;
   }
  }
 }
 if(Math.abs(inputArea-outputArea)>Math.max(.02,inputArea*1e-7))throw Error('Orthophoto partition lost TIN coverage');
 return {parts:parts.map(({keys,...p})=>p),inputArea,outputArea,triangles};
}
