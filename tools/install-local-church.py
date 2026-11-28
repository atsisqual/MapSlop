#!/usr/bin/env python3
"""Install one verified local GLB into a COPY of an approved runtime, preserving colliders."""
import argparse, hashlib, json, shutil
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def patch(s,old,new):
    if s.count(old)!=1:raise ValueError("Unexpected runtime patch anchor: "+old[:120])
    return s.replace(old,new)

def main():
    p=argparse.ArgumentParser();p.add_argument("--runtime",type=Path,required=True);p.add_argument("--candidate",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    report=json.loads((a.candidate/"church-report.json").read_text());model=a.candidate/"church.glb"
    if not report["pass"] or report["fixture"] or report["osm_id"]!=149406360 or sha(model)!=report["glb_sha256"]:raise ValueError("Church candidate is not verified")
    if a.output.exists():raise ValueError("Never overwrite an existing runtime")
    shutil.copytree(a.runtime,a.output)
    models=a.output/"models";models.mkdir();shutil.copy2(model,models/"church.glb")
    b=a.output/"js/pedome-buildings-detail.mjs";s=b.read_text()
    s=patch(s,"  for(const b of GEO.buildings){","""  let churchReplacement=null;
  for(const b of GEO.buildings){
    const replaceChurch=String(b.id)==='149406360';
    const previous=replaceChurch?new Map([...buckets].map(([m,pos])=>[m,pos.length])):null;
    const windowStart=windows.length,doorStart=doors.length;""")
    s=patch(s,"  }\n  let shell=0;","""    if(replaceChurch){
      let removed=0;
      for(const [m,pos] of buckets){const n=previous.get(m)??0;removed+=(pos.length-n)/9;pos.length=n;}
      const removedWindows=windows.length-windowStart,removedDoors=doors.length-doorStart;
      windows.length=windowStart;doors.length=doorStart;
      churchReplacement={osm_id:149406360,removed_shell_triangles:removed,removed_windows:removedWindows,removed_doors:removedDoors,physics_row:rows.at(-1)};
      if(removed<=0)throw Error('Church source visual not found');
    }
  }
  if(!churchReplacement)throw Error('Church OSM id missing from runtime');
  group.userData.churchReplacement=churchReplacement;
  let shell=0;""")
    b.write_text(s)
    shell=a.output/"js/pedome.js";s=shell.read_text()
    s=patch(s,"import { installPedomeUI } from './pedome-ui.js';","import { installPedomeUI } from './pedome-ui.js';\nimport { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';")
    old="const buildingGroup=await buildBuildings(); scene.add(buildingGroup); window.buildingDetailReport=buildingGroup.userData.buildingDetailReport;"
    new=old+"""
 const loadedChurch=await new GLTFLoader().loadAsync(new URL('../models/church.glb',import.meta.url).href);
 loadedChurch.scene.name='PedomeChurchMeasuredVisual';buildingGroup.add(loadedChurch.scene);
 buildingGroup.updateMatrixWorld(true);const churchBounds=new THREE.Box3().setFromObject(loadedChurch.scene);
 let churchMeshes=0,churchTriangles=0;const pbrMaterials=[],roofMaterials=[];loadedChurch.scene.traverse(o=>{if(o.isMesh){churchMeshes++;churchTriangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;for(const mat of (Array.isArray(o.material)?o.material:[o.material])){if(mat?.map&&mat.normalMap&&mat.roughnessMap)pbrMaterials.push({name:mat.name,uv:!!o.geometry.attributes.uv});if(mat?.name?.includes('Measured_roof')||mat?.name?.includes('Measured roof'))roofMaterials.push({name:mat.name,uv:!!o.geometry.attributes.uv,baseColor:mat.color.toArray(),baseMap:!!mat.map,colorSpace:mat.map?.colorSpace,dimensions:[mat.map?.image?.width,mat.map?.image?.height],emissiveMap:!!mat.emissiveMap&&mat.emissiveMap.source===mat.map?.source,emissive:mat.emissive?.toArray(),metalness:mat.metalness,roughness:mat.roughness});}}});
 window.churchVisualReport={...buildingGroup.userData.churchReplacement,mesh_count:churchMeshes,pbr_materials:pbrMaterials,roof_materials:roofMaterials,triangles:churchTriangles,bounds:[churchBounds.min.toArray(),churchBounds.max.toArray()],sha256:CHURCH_SHA};
 if(roofMaterials.length!==1||!roofMaterials[0].baseMap||!roofMaterials[0].uv||roofMaterials[0].colorSpace!==THREE.SRGBColorSpace||!roofMaterials[0].emissiveMap||churchMeshes<2||!window.churchVisualReport.bounds.flat().every(Number.isFinite))throw Error('Invalid church GLB');"""
    s=patch(s,old,new.replace("CHURCH_SHA",json.dumps(report["glb_sha256"])))
    shell.write_text(s)
    changed=[p.relative_to(a.runtime).as_posix() for p in a.runtime.rglob("*") if p.is_file() and sha(p)!=sha(a.output/p.relative_to(a.runtime))]
    if set(changed)!={"js/pedome.js","js/pedome-buildings-detail.mjs"}:raise ValueError("Unexpected runtime changes: "+str(changed))
    print("CHURCH_INSTALL",json.dumps({"changed":changed,"model":report["glb_sha256"],"physics_unchanged":True}))
if __name__=="__main__":main()
