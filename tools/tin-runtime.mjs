// Spatial lookup and interpolation over the exported pydelatin faces.
// This does not triangulate; it uses precisely the triangles sent to Three.js.
export function makeTin(T){
  const v=T.vertices,f=T.triangles,bins=new Map(),B=16;
  const x1=T.x0+(T.nx-1)*T.cell,z1=T.z0+(T.nz-1)*T.cell;
  const key=(x,z)=>x+','+z;
  const normals=new Float32Array(v.length);
  for(let i=0;i<f.length;i+=3){
    const a=f[i]*3,b=f[i+1]*3,c=f[i+2]*3;
    const x0=Math.min(v[a],v[b],v[c]),xx=Math.max(v[a],v[b],v[c]);
    const z0=Math.min(v[a+2],v[b+2],v[c+2]),zz=Math.max(v[a+2],v[b+2],v[c+2]);
    for(let x=Math.floor(x0/B);x<=Math.floor(xx/B);x++)for(let z=Math.floor(z0/B);z<=Math.floor(zz/B);z++){
      const k=key(x,z);if(!bins.has(k))bins.set(k,[]);bins.get(k).push(i);
    }
    const dx=v[b]-v[a],dy=v[b+1]-v[a+1],dz=v[b+2]-v[a+2];
    const ex=v[c]-v[a],ey=v[c+1]-v[a+1],ez=v[c+2]-v[a+2];
    for(const j of [a,b,c]){
      normals[j]+=dy*ez-dz*ey;normals[j+1]+=dz*ex-dx*ez;normals[j+2]+=dx*ey-dy*ex;
    }
  }
  for(let i=0;i<normals.length;i+=3){
    const l=Math.hypot(normals[i],normals[i+1],normals[i+2])||1;
    for(let k=0;k<3;k++)normals[i+k]/=l;
  }
  const faces=(minX,minZ,maxX,maxZ)=>{
    const seen=new Set();
    for(let x=Math.floor(Math.max(T.x0,minX)/B);x<=Math.floor(Math.min(x1,maxX)/B);x++)
      for(let z=Math.floor(Math.max(T.z0,minZ)/B);z<=Math.floor(Math.min(z1,maxZ)/B);z++)
        for(const i of bins.get(key(x,z))||[])seen.add(i);
    return seen;
  };
  const triangle=i=>{
    const a=f[i]*3,b=f[i+1]*3,c=f[i+2]*3;
    // CCW x,z for the existing polygon clipper (render faces face up).
    return [v[a],v[a+2],v[c],v[c+2],v[b],v[b+2]];
  };
  function find(x,z){
    x=Math.max(T.x0,Math.min(x1,x));z=Math.max(T.z0,Math.min(z1,z));
    for(const i of bins.get(key(Math.floor(x/B),Math.floor(z/B)))||[]){
      const a=f[i]*3,b=f[i+1]*3,c=f[i+2]*3;
      const dx=v[b]-v[a],dz=v[b+2]-v[a+2],ex=v[c]-v[a],ez=v[c+2]-v[a+2];
      const det=dx*ez-dz*ex;
      const u=((x-v[a])*ez-(z-v[a+2])*ex)/det,w=(dx*(z-v[a+2])-dz*(x-v[a]))/det;
      if(Math.min(u,w,1-u-w)>=-1e-8)return [a,b,c,u,w];
    }
    throw Error('TIN coverage hole');
  }
  return {faces,triangle,normals,
    heightAt(x,z){
      const [a,b,c,u,w]=find(x,z);
      return v[a+1]+u*(v[b+1]-v[a+1])+w*(v[c+1]-v[a+1]);
    },
    normalAt(x,z,out){
      const [a,b,c,u,w]=find(x,z);
      for(let k=0;k<3;k++)out[k]=(1-u-w)*normals[a+k]+u*normals[b+k]+w*normals[c+k];
      const l=Math.hypot(...out)||1;
      for(let k=0;k<3;k++)out[k]/=l;
      return out;
    },
    segmentBreaks(ax,az,bx,bz){
      const ts=[0,1],dx=bx-ax,dz=bz-az;
      for(const i of faces(Math.min(ax,bx),Math.min(az,bz),Math.max(ax,bx),Math.max(az,bz))){
        const p=triangle(i);
        for(let j=0;j<6;j+=2){
          const k=(j+2)%6,ex=p[k]-p[j],ez=p[k+1]-p[j+1];
          const det=dx*ez-dz*ex;if(Math.abs(det)<1e-10)continue;
          const ox=p[j]-ax,oz=p[j+1]-az;
          const t=(ox*ez-oz*ex)/det,u=(ox*dz-oz*dx)/det;
          if(t>1e-8&&t<1-1e-8&&u>=-1e-8&&u<=1+1e-8)ts.push(t);
        }
      }
      ts.sort((a,b)=>a-b);return ts.filter((v,i)=>!i||v-ts[i-1]>1e-8);
    }
  };
}
