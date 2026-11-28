import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {NodeIO} from '@gltf-transform/core';
import {ALL_EXTENSIONS} from '@gltf-transform/extensions';
import {textureCompress} from '@gltf-transform/functions';
import sharp from 'sharp';
const root=process.argv[2],src=path.join(root,'church.glb'),tmp=path.join(root,'church-webp.glb');
const io=new NodeIO().registerExtensions(ALL_EXTENSIONS);
const hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const bytes=a=>Buffer.from(a.buffer,a.byteOffset,a.byteLength);
const signature=d=>d.getRoot().listMeshes().map(m=>m.listPrimitives().map(p=>({mode:p.getMode(),attributes:p.listSemantics().sort().map(k=>[k,hash(bytes(p.getAttribute(k).getArray()))]),indices:p.getIndices()?hash(bytes(p.getIndices().getArray())):null,material:p.getMaterial()?.getName()})));
const slots=['BaseColor','Normal','MetallicRoughness','Occlusion','Emissive'];
const maps=d=>d.getRoot().listMaterials().map(m=>({name:m.getName(),base:m.getBaseColorFactor(),emissive:m.getEmissiveFactor(),metal:m.getMetallicFactor(),rough:m.getRoughnessFactor(),normalScale:m.getNormalScale(),textures:slots.map(k=>{const t=m['get'+k+'Texture']();const i=m['get'+k+'TextureInfo']();return t?{slot:k,index:d.getRoot().listTextures().indexOf(t),texCoord:i.getTexCoord(),wrapS:i.getWrapS(),wrapT:i.getWrapT()}:null})}));
const doc=await io.read(src);const original=fs.readFileSync(src),geo=signature(doc),materials=maps(doc);
const old=doc.getRoot().listTextures().map(t=>({image:Buffer.from(t.getImage()),mime:t.getMimeType(),size:t.getSize()}));
await doc.transform(textureCompress({encoder:sharp,targetFormat:'webp',lossless:true}));
const stats=[];
async function decoded(b){return sharp(b).ensureAlpha().raw().toBuffer();}
for(const [i,t] of doc.getRoot().listTextures().entries()){
 const o=old[i],candidate=Buffer.from(t.getImage()),size=t.getSize();
 const equal=JSON.stringify(size)===JSON.stringify(o.size)&&Buffer.compare(await decoded(candidate),await decoded(o.image))===0;
 if(!equal||candidate.length>=o.image.length)t.setImage(o.image).setMimeType(o.mime);
 stats.push({index:i,dimensions:o.size,source_bytes:o.image.length,output_bytes:t.getImage().length,source_mime:o.mime,output_mime:t.getMimeType(),candidate_pixel_exact:equal,decoded_rgba_bytes:o.size[0]*o.size[1]*4});
}
if(!doc.getRoot().listTextures().some(t=>t.getMimeType()==='image/webp'))for(const e of doc.getRoot().listExtensionsUsed())if(e.extensionName==='EXT_texture_webp')e.dispose();
await io.write(tmp,doc);
const round=await io.read(tmp);
if(JSON.stringify(signature(round))!==JSON.stringify(geo)||JSON.stringify(maps(round))!==JSON.stringify(materials))throw Error('Geometry/UV/material regression during optimization');
for(const [i,t] of round.getRoot().listTextures().entries()){
 if(JSON.stringify(t.getSize())!==JSON.stringify(old[i].size)||Buffer.compare(await decoded(t.getImage()),await decoded(old[i].image))!==0)throw Error('Decoded texture regression');
}
const optimized=fs.readFileSync(tmp),use=optimized.length<original.length;
if(use)fs.renameSync(tmp,src);else fs.unlinkSync(tmp);
const out=fs.readFileSync(src);
const report=JSON.parse(fs.readFileSync(path.join(root,'church-report.json'),'utf8'));
report.optimization={engine:'glTF-Transform 4.1.1 / sharp 0.34.5',policy:'lossless WebP where smaller, no resizing or geometry quantization; retain originals otherwise',source_bytes:original.length,candidate_bytes:optimized.length,selected_bytes:out.length,selected:use?'webp':'original',source_sha256:hash(original),sha256:hash(out),geometry_uv_materials_unchanged:true,decoded_pixels_unchanged:true,textures:stats,estimated_rgba8_base_bytes:old.reduce((a,t)=>a+t.size[0]*t.size[1]*4,0),target_bytes_advisory:1000000};
report.glb_sha256=hash(out);report.glb_bytes=out.length;
fs.writeFileSync(path.join(root,'church-report.json'),JSON.stringify(report,null,2)+'\n');
fs.writeFileSync(path.join(root,'optimization-report.json'),JSON.stringify(report.optimization,null,2)+'\n');
console.log('CHURCH_OPTIMIZATION',JSON.stringify(report.optimization));
