import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {TilesRenderer} from '3d-tiles-renderer/three';
const mode=new URLSearchParams(location.search).get('mode')==='tiles'?'tiles':'glb';
const status=document.querySelector('#status');
const report=await fetch('./church-report.json').then(r=>{if(!r.ok)throw Error('Missing report');return r.json()});
if(!report.pass)throw Error('Candidate rejected');
const scene=new THREE.Scene();scene.background=new THREE.Color(0xc9d2d9);
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(Math.min(devicePixelRatio,2));document.body.appendChild(renderer.domElement);
const camera=new THREE.PerspectiveCamera(45,innerWidth/innerHeight,.1,1000);
const lo=new THREE.Vector3(...report.bounds[0]),hi=new THREE.Vector3(...report.bounds[1]),center=lo.clone().add(hi).multiplyScalar(.5);
camera.position.copy(center).add(new THREE.Vector3(36,31,42));
const controls=new OrbitControls(camera,renderer.domElement);controls.target.copy(center);controls.update();
scene.add(new THREE.HemisphereLight(0xffffff,0x777366,2));
const sun=new THREE.DirectionalLight(0xffffff,2.4);sun.position.set(-30,55,35);scene.add(sun);
const state={mode,ready:false,error:null,report,models:0,bounds:null};
window.localMesh=state;
const measure=o=>{o.updateMatrixWorld(true);const box=new THREE.Box3().setFromObject(o);state.bounds=[box.min.toArray(),box.max.toArray()];let count=0;o.traverse(n=>{if(n.isMesh)count++});state.meshes=count;state.ready=count>0&&state.bounds.flat().every(Number.isFinite);status.textContent=(report.fixture?'SINTÉTICO — ':'DGT / OSM — ')+mode+' · '+(report.roof_triangles+report.wall_triangles)+' triângulos · fachadas estimadas';};
let tiles=null;
try{
 if(mode==='glb'){
  const model=await new GLTFLoader().loadAsync('./church.glb');scene.add(model.scene);state.models=1;measure(model.scene);
 }else{
  tiles=new TilesRenderer('./tileset.json');tiles.group.rotation.x=-Math.PI/2;scene.add(tiles.group);tiles.setCamera(camera);tiles.setResolution(camera,innerWidth,innerHeight);
  tiles.addEventListener('load-model',()=>{state.models++;measure(tiles.group)});
  tiles.addEventListener('load-error',e=>{state.error=String(e.error||'Tile load error')});
 }
}catch(e){state.error=String(e);status.textContent=state.error;throw e;}
addEventListener('resize',()=>{renderer.setSize(innerWidth,innerHeight);camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();tiles?.setResolution(camera,innerWidth,innerHeight)});
renderer.setAnimationLoop(()=>{controls.update();camera.updateMatrixWorld();tiles?.update();renderer.render(scene,camera);if(tiles&&state.models&&!state.ready)measure(tiles.group)});
