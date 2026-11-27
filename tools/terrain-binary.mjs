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
  }else if(enc==='tin-morton-cm-f32bits-varint'&&t.kind==='tin'){
    const nv=t.vertex_count,nt=t.triangle_count,lengths=t.stream_lengths;
    delete t.vertex_count;delete t.triangle_count;delete t.stream_lengths;
    if(!Number.isInteger(nv)||!Number.isInteger(nt)||nv<4||nv>=150000||nt<2||nt>2*nv||
       !Array.isArray(lengths)||lengths.length!==6||lengths.some(n=>!Number.isInteger(n)||n<1)||
       lengths.reduce((a,b)=>a+b,0)!==data.byteLength-offset)throw Error('Compact terrain counts/lengths');
    const streams=[];let pos=offset;
    for(let s=0;s<6;s++){
      const end=pos+lengths[s],count=s<3?nv:nt,values=new Float64Array(count);
      let prev=0;
      for(let i=0;i<count;i++){
        let v=0,done=false;
        for(let shift=0;shift<35;shift+=7){
          if(pos>=end)throw Error('Truncated compact terrain stream');
          const b=view.getUint8(pos++);v+=(b&127)*2**shift;
          if(!(b&128)){done=true;break;}
        }
        if(!done||v>=2**33)throw Error('Compact terrain varint');
        if(s<4){prev+=v%2===0?v/2:-(v+1)/2;values[i]=prev;}
        else values[i]=v;
      }
      if(pos!==end)throw Error('Trailing compact terrain bytes');
      streams.push(values);
    }
    const [xs,ys,zs,aa,bb,cc]=streams;
    t.vertices=new Float32Array(3*nv);t.triangles=new Uint32Array(3*nt);
    const scratch=new DataView(new ArrayBuffer(4));
    for(let i=0;i<nv;i++){
      if(Math.abs(xs[i])>100000000||Math.abs(zs[i])>100000000||ys[i]<0||ys[i]>=2**32)throw Error('Compact terrain coordinate/height range');
      scratch.setUint32(0,ys[i],true);const y=scratch.getFloat32(0,true);
      if(!Number.isFinite(y))throw Error('Compact terrain nonfinite height');
      t.vertices[3*i]=xs[i]/100;t.vertices[3*i+1]=y;t.vertices[3*i+2]=zs[i]/100;
    }
    for(let i=0;i<nt;i++){
      const a=aa[i],b=a+bb[i],c=a+cc[i];
      if(!(a>=0&&b>a&&c>a&&b<nv&&c<nv&&b!==c))throw Error('Compact terrain index');
      t.triangles[3*i]=a;t.triangles[3*i+1]=b;t.triangles[3*i+2]=c;
    }
  }else if(enc==='height-f32le-implicit-grid'&&(t.kind||'grid')==='grid'){
    const c=t.height_count;delete t.height_count;
    if(!Number.isInteger(c)||c!==t.nx*t.nz||c<4||c>1500000||data.byteLength!==offset+c*4)throw Error('Terrain grid size');
    t.heights=new Float32Array(c);
    for(let i=0;i<c;i++)t.heights[i]=view.getFloat32(offset+i*4,true);
  }else throw Error('Unknown terrain encoding');
  return t;
}
function decodeMeasured(data){
  const memory=()=>typeof performance.memory?.usedJSHeapSize==='number'?performance.memory.usedJSHeapSize:null;
  const before=memory(),start=performance.now(),t=decodeTerrain(data);
  const duration=performance.now()-start,after=memory();
  const n=new DataView(data).getUint32(8,true);
  const encoding=JSON.parse(new TextDecoder().decode(new Uint8Array(data,12,n))).encoding;
  t.decodeMetrics={encoding,decode_ms:duration,input_bytes:data.byteLength,
    output_typed_array_bytes:(t.vertices?.byteLength||0)+(t.triangles?.byteLength||0)+(t.heights?.byteLength||0),
    compact_scratch_stream_bytes:encoding==='tin-morton-cm-f32bits-varint'?8*(t.vertices.length+t.triangles.length):0,
    js_heap_before_bytes:before,js_heap_after_bytes:after,js_heap_method:before===null?'unavailable':'Chromium performance.memory (approximate, not peak; excludes some buffers)'};
  return t;
}
export async function loadTerrain(url){
  if(typeof window==='undefined'&&typeof process!=='undefined'&&process.versions?.node){
    const {readFile}=await import('node:fs/promises');
    const b=await readFile(url);
    return decodeMeasured(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength));
  }
  const response=await fetch(url);
  if(!response.ok)throw Error('Terrain download '+response.status);
  return decodeMeasured(await response.arrayBuffer());
}
