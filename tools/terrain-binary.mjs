// MSLTERR1 decoder: the browser downloads the actual binary, not an expanded JS array.
export function decodeTerrain(data){
  const view=new DataView(data);
  if(data.byteLength<12||data.byteLength>32000000||new TextDecoder().decode(new Uint8Array(data,0,8))!=='MSLTERR1')throw Error('Terrain binary magic/size');
  const n=view.getUint32(8,true),offset=12+Math.ceil(n/4)*4;
  if(n<2||n>65536||offset>data.byteLength)throw Error('Terrain header size');
  const t=JSON.parse(new TextDecoder().decode(new Uint8Array(data,12,n)));
  const enc=t.encoding;delete t.encoding;
  if(enc==='xyz-f32le-index-u32le'&&t.kind==='tin'){
    const nv=t.vertex_count,nt=t.triangle_count;delete t.vertex_count;delete t.triangle_count;
    if(!Number.isInteger(nv)||!Number.isInteger(nt)||nv<4||nv>=150000||nt<2||nt>2*nv||data.byteLength!==offset+12*(nv+nt))throw Error('Terrain TIN size');
    t.vertices=new Float32Array(3*nv);t.triangles=new Uint32Array(3*nt);
    for(let i=0;i<t.vertices.length;i++)t.vertices[i]=view.getFloat32(offset+i*4,true);
    for(let i=0;i<t.triangles.length;i++){const v=view.getUint32(offset+nv*12+i*4,true);if(v>=nv)throw Error('Terrain index');t.triangles[i]=v;}
  }else if(enc==='height-f32le-implicit-grid'&&(t.kind||'grid')==='grid'){
    const c=t.height_count;delete t.height_count;
    if(!Number.isInteger(c)||c!==t.nx*t.nz||c<4||c>1500000||data.byteLength!==offset+c*4)throw Error('Terrain grid size');
    t.heights=new Float32Array(c);
    for(let i=0;i<c;i++)t.heights[i]=view.getFloat32(offset+i*4,true);
  }else throw Error('Unknown terrain encoding');
  return t;
}
export async function loadTerrain(url){
  if(typeof window==='undefined'&&typeof process!=='undefined'&&process.versions?.node){
    const {readFile}=await import('node:fs/promises');
    const b=await readFile(url);
    return decodeTerrain(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength));
  }
  const response=await fetch(url);
  if(!response.ok)throw Error('Terrain download '+response.status);
  return decodeTerrain(await response.arrayBuffer());
}
