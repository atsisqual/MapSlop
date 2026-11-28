#!/usr/bin/env python3
"""MapSlop P0 adapter for the inspected Nairobi archive. Python 3 + Node 22.
No PortoSlop code or data is used. Default downloads real OSM; fixture is testing only.
"""
import argparse, json, math, pathlib, re, shutil, subprocess, urllib.request, urllib.parse
from terrain_grid import validate as validate_terrain
from terrain_binary import decode as decode_terrain
P=pathlib.Path
BBOX=(41.4105,-8.395,41.4195,-8.383)
LAT,LON=41.41501,-8.38809 # church; OSM way 149406360
ROAD='motorway|trunk|primary|secondary|tertiary|unclassified|residential|service|living_street|pedestrian|footway|path|cycleway|steps|track'
B=','.join(map(str,BBOX))
CLAUSES=[f'way["highway"~"^({ROAD})(_link)?$"]({B})',f'nwr["building"]({B})',f'nwr["building:part"]({B})',f'relation["type"="building"]({B})',f'nwr["landuse"]({B})',f'nwr["natural"]({B})',f'nwr["leisure"]({B})',f'nwr["amenity"]({B})',f'nwr["tourism"]({B})',f'nwr["historic"]({B})',f'node["highway"]({B})',f'way["waterway"]({B})',f'nwr["railway"]({B})',f'way["footway"="crossing"]({B})']
QUERY='[out:json][timeout:90];('+';'.join(CLAUSES)+';);out geom;'

def run(*cmd,cwd=None): subprocess.run(cmd,cwd=cwd,check=True)
def write(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False),encoding='utf-8')
def patch(path,old,new):
    s=path.read_text(encoding='utf-8')
    if s.count(old)!=1: raise ValueError(f'Upstream changed: {path.name}: {old[:90]}')
    path.write_text(s.replace(old,new,1),encoding='utf-8')
def fixture():
    def way(i,t,pts,ids): return dict(type='way',id=i,tags=t,nodes=ids,geometry=[dict(lat=a,lon=b) for a,b in pts])
    return {'elements':[
      way(1,{'highway':'residential','name':'TESTE — via fictícia'},[(LAT-.002,LON),(LAT,LON),(LAT+.002,LON+.001)],[1,2,3]),
      way(2,{'highway':'residential','name':'TESTE — cruzamento'},[(LAT,LON-.002),(LAT,LON),(LAT,LON+.002)],[4,2,5]),
      way(3,{'building':'house','building:levels':'2'},[(LAT+.0004,LON+.0002),(LAT+.0004,LON+.0004),(LAT+.0006,LON+.0004),(LAT+.0006,LON+.0002),(LAT+.0004,LON+.0002)],[6,7,8,9,6]) ]}
def get_osm():
    for endpoint in ['https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter']:
        try:
            req=urllib.request.Request(endpoint,data=urllib.parse.urlencode({'data':QUERY}).encode(),headers={'User-Agent':'MapSlop/0.1 (interactive geographic prototype)'})
            with urllib.request.urlopen(req,timeout=120) as r: return json.load(r)
        except Exception as e: print(endpoint,e)
    raise RuntimeError('Não foi possível obter OSM. Guarda a resposta Overpass JSON e usa --osm-json.')
def flat_dem():
    s,w,n,e=BBOX; step=.00025; nx=math.ceil((e-w+.02)/step); ny=math.ceil((n-s+.02)/step)
    return dict(source='SYNTHETIC FLAT TEST TERRAIN',west=w-.01,north=n+.01,dx=step,dy=-step,nx=nx,ny=ny,values=[0]*(nx*ny))
def main():
    p=argparse.ArgumentParser(); p.add_argument('upstream',type=P); p.add_argument('output',type=P); p.add_argument('--osm-json',type=P); p.add_argument('--dem-json',type=P); p.add_argument('--terrain-json',type=P,help='Legacy precomputed JSON terrain'); p.add_argument('--terrain-bin',type=P,help='MSLTERR1 binary terrain'); p.add_argument('--building-preview',action='store_true',help='Private height preview, preserve centimetres'); p.add_argument('--roof-preview',type=P,help='Private semantic roof preview JSON'); p.add_argument('--flat',action='store_true'); p.add_argument('--fixture',action='store_true'); p.add_argument('--three-vendor',type=P,help='Optional local Three.js tree (experimental version compatibility)'); p.add_argument('--traffic-preview',action='store_true',help='Private traffic evidence only'); a=p.parse_args()
    if a.output.exists(): p.error('output must not exist; no existing files overwritten')
    if a.fixture and a.osm_json: p.error('fixture and osm-json are mutually exclusive')
    if (a.terrain_json or a.terrain_bin) and (a.dem_json or a.flat or a.fixture or (a.terrain_json and a.terrain_bin)): p.error('terrain input is exclusive with other terrain modes')
    terrain=validate_terrain(decode_terrain(a.terrain_bin.read_bytes())) if a.terrain_bin else validate_terrain(json.loads(a.terrain_json.read_text(encoding='utf-8'))) if a.terrain_json else None
    src=a.upstream.resolve(); out=a.output.resolve()
    data=fixture() if a.fixture else json.loads(a.osm_json.read_text(encoding='utf-8-sig')) if a.osm_json else get_osm()
    els=data.get('elements');
    if not isinstance(els,list) or data.get('remark'): raise ValueError('Invalid/partial Overpass result')
    def t(e): return e.get('tags',{})
    def road(e): return e['type']=='way' and t(e).get('highway','').removesuffix('_link') in ROAD.split('|') and len(e.get('geometry',[]))>=2 and len(e.get('nodes',[]))==len(e['geometry'])
    def area(e): return e['type']!='node' and (t(e).get('leisure') in ['park','garden','pitch','stadium'] or t(e).get('landuse') in ['grass','forest','recreation_ground','cemetery'] or t(e).get('natural') in ['water','wood','scrub','grassland'] or t(e).get('amenity')=='parking')
    groups={'roads':road,'buildings':lambda e:'building' in t(e),'building_parts':lambda e:'building:part' in t(e) or t(e).get('type')=='building','areas':area,'landmarks':lambda e:bool(t(e).get('name')) and any(k in t(e) for k in ['tourism','historic','amenity','building']),'street':lambda e:t(e).get('highway') in ['traffic_signals','crossing','street_lamp'] or t(e).get('crossing')=='traffic_signals' or t(e).get('footway')=='crossing' or t(e).get('natural') in ['tree','tree_row'],'water_rail':lambda e:bool(t(e).get('waterway') or t(e).get('railway') in ['rail','light_rail','platform','station','halt'] or t(e).get('highway')=='bus_stop' or t(e).get('amenity')=='bus_station')}
    selected={k:[e for e in els if fn(e)] for k,fn in groups.items()}
    if not selected['roads'] or not selected['buildings']: raise ValueError('Empty roads/buildings; check coverage')
    for folder in ['js','css','tools']:
        shutil.copytree(src/folder,out/folder,ignore=shutil.ignore_patterns('data','nairobi-models.bin','nairobi-geodata.js','nairobi-models.js'))
    for f in ['index.html','README.md','package.json','package-lock.json']:
        shutil.copy2(src/f,out/f)
    shutil.copy2(src/'README.md',out/'UPSTREAM-README.md')
    if (src/'LICENSE').exists(): shutil.copy2(src/'LICENSE',out/'LICENSE.upstream')
    (out/'tools/data').mkdir()
    for k,v in selected.items(): write(out/f'tools/data/osm_{k}.json',{'elements':v})
    write(out/'tools/bbox.json',dict(zip(['south','west','north','east'],BBOX)))
    if a.dem_json: shutil.copy2(a.dem_json,out/'tools/data/dem_glo30.json')
    elif a.flat or a.fixture or terrain: write(out/'tools/data/dem_glo30.json',flat_dem())
    else:
        run('npm.cmd' if __import__('os').name=='nt' else 'npm','ci',cwd=out)
        run('node','tools/fetch-terrain.mjs',cwd=out)
    dem=json.loads((out/'tools/data/dem_glo30.json').read_text()); vals=dem['values']; nx=dem['nx']; ny=dem['ny']
    if nx<2 or ny<2 or len(vals)!=nx*ny or any(not math.isfinite(v) or abs(v)>9000 for v in vals): raise ValueError('Invalid DEM')
    if not (dem['dx']>0 and dem['dy']<0 and dem['west']<=BBOX[1] and dem['west']+dem['dx']*nx>=BBOX[3] and dem['north']>=BBOX[2] and dem['north']+dem['dy']*ny<=BBOX[0]): raise ValueError('DEM does not cover Pedome')
    f=out/'tools/build-geodata.mjs'
    patch(f,'const LAT0 = -1.28866;',f'const LAT0 = {LAT};'); patch(f,'const LON0 = 36.82307;',f'const LON0 = {LON};')
    patch(f,"origin: 'Kenyatta International Convention Centre'","origin: 'Pedome — Igreja de São Pedro'"); patch(f,"drivesOn: 'left'","drivesOn: 'right'")
    patch(f,'if (d < CORE_R && area > 250) return Math.round(4 + r * r * 10); // 4..14, skewed low','if (area > 250) return 1 + (r > 0.65 ? 1 : 0); // conservative rural estimate')
    patch(f,'if (d < CORE_R * 1.6 && area > 150) return Math.round(2 + r * 4); // 2..6','if (area > 150) return 1 + (r > 0.5 ? 1 : 0);')
    patch(f,'if (!sight && !(b && b.h > 40)) continue;','if (!sight && !b) continue;')
    # Keep measured building heights to centimetres; upstream q() rounds to decimetres.
    if a.building_preview: patch(f,'const b = { id: el.id, ring: flat(r), h: q(h) };','const b = { id: el.id, ring: flat(r), h: Math.round(h * 100) / 100 };')
    run('node','tools/build-geodata.mjs',cwd=out)
    geo_path=out/'js/nairobi-geodata.js'; gs=geo_path.read_text(); geo=json.loads(gs.split('export const GEO = ',1)[1].strip().removesuffix(';'))
    if not geo['roadGraph']['links'] or not geo['buildings']: raise ValueError('Map has no usable road graph or buildings')
    if terrain: geo['terrain']=terrain
    if terrain and terrain.get('kind')=='tin':
        shutil.copy2(P(__file__).resolve().parent/'tin-runtime.mjs',out/'js/tin-runtime.mjs')
        f=out/'js/terrain.js'
        patch(f,'const T = GEO.terrain;',"""import { makeTin } from './tin-runtime.mjs';
const T = GEO.terrain;
export const tin = T.kind === 'tin' ? makeTin(T) : null;""")
        patch(f,'export function heightAt(x, z) {','export function heightAt(x, z) {\n  if(tin) return tin.heightAt(x,z);')
        patch(f,'function normals() {','function normals() {\n  if(tin) return tin.normals;')
        patch(f,'export function terrainNormal(x, z, out = [0, 1, 0]) {','export function terrainNormal(x, z, out = [0, 1, 0]) {\n  if(tin) return tin.normalAt(x,z,out);')
        f=out/'js/ground.js'
        s=f.read_text()
        start=s.index('  const pos = new Float32Array(T.nx * T.nz * 3);')
        end=s.index("  geo.setAttribute('position'",start)
        old=s[start:end]
        # Keep the upstream grid path unchanged and use the actual TIN vertex/index buffers.
        s=s[:start]+"""  let pos, uv, index;
  if(T.kind==='tin'){
    pos=new Float32Array(T.vertices);
    uv=new Float32Array(pos.length/3*2);
    for(let i=0;i<pos.length/3;i++) uv.set([(pos[3*i]-T.x0)/W,1-(pos[3*i+2]-T.z0)/H],2*i);
    index=Array.from(T.triangles);
  } else {
"""+old.replace('const pos =','pos =').replace('const uv =','uv =').replace('const index =','index =')+"""  }
"""+s[end:]
        f.write_text(s,encoding='utf-8')
        f=out/'js/street-geometry.js'
        patch(f,"import { heightAt, terrainNormal } from './terrain.js';","import { heightAt, terrainNormal, tin } from './terrain.js';")
        patch(f,'export function drape(p, fn) {',"""export function drape(p, fn) {
  if(tin){
    const b=bounds(p);
    for(const i of tin.faces(b.minX,b.minZ,b.maxX,b.maxZ)){
      const tri=tin.triangle(i);
      let q=p;
      for(let j=0;j<6 && q;j+=2){
        const k=(j+2)%6,dx=tri[k]-tri[j],dz=tri[k+1]-tri[j+1];
        q=clip(q,dz,-dx,dz*tri[j]-dx*tri[j+1]);
      }
      if(q) fn(q);
    }
    return;
  }""")
        patch(f,'function segmentBreaks(ax, az, bx, bz) {','function segmentBreaks(ax, az, bx, bz) {\n  if(tin) return tin.segmentBreaks(ax,az,bx,bz);')

    if a.roof_preview:
        if not a.building_preview or not a.terrain_bin or not terrain or terrain.get('kind')!='tin':
            p.error('--roof-preview requires --building-preview and verified TIN')
        geo['roofPreview']=json.loads(a.roof_preview.read_text())
        source_tags={str(e['id']):e.get('tags',{}) for e in data['elements'] if e.get('type')=='way'}
        for b in geo['buildings']:
            t=source_tags.get(str(b['id']),{})
            b['roofOnly']=t.get('building')=='roof' or t.get('building:part')=='roof'
            b['explicitMinH']='min_height' in t or 'building:min_level' in t
        shutil.copy2(P(__file__).resolve().parent/'pedome-buildings-detail.mjs',out/'js/pedome-buildings-detail.mjs')
        f=out/'js/buildings.js'
        patch(f,'export function footings() {',"import { detailBases } from './pedome-buildings-detail.mjs';\nexport function footings() {\n  if(detailBases.size) return detailBases;")
    geo['frame']['testFixture']=a.fixture; geo['frame']['flatTerrain']=bool(a.flat or a.fixture); geo['frame']['demSource']=terrain['source'] if terrain else dem.get('source','unknown');
    if a.terrain_bin:
        shutil.copy2(a.terrain_bin,out/'js/terrain.bin')
        shutil.copy2(P(__file__).resolve().parent/'terrain-binary.mjs',out/'js/terrain-binary.mjs')
        exported={**geo,'terrain':None}
        geo_path.write_text("import { loadTerrain } from './terrain-binary.mjs';\nexport const GEO = "+json.dumps(exported,ensure_ascii=False)+";\nGEO.terrain = await loadTerrain(new URL('./terrain.bin',import.meta.url));\n",encoding='utf-8')
    else:
        geo_path.write_text('// Geographic data © OpenStreetMap contributors, ODbL 1.0 (real mode). See upstream README for terrain attribution.\nexport const GEO = '+json.dumps(geo,ensure_ascii=False)+';\n',encoding='utf-8')
    (out/'js/nairobi-models.js').write_text('export const MODEL_HEIGHTS = {};\nexport const MODEL_BUILDINGS = [];\n')
    # Localise road graph, turn priority and paint together. No physics change.
    shutil.copy2(P(__file__).resolve().parent/'traffic-side.mjs',out/'js/traffic-side.mjs')
    f=out/'js/road-network.js'
    patch(f,"import { GEO } from './nairobi-geodata.js';","import { GEO } from './nairobi-geodata.js';\nimport { rightLanes, rightOf } from './traffic-side.mjs';")
    patch(f,'const each = Array.from({ length: n }, (_, i) => -(step / 2 + (n - 1 - i) * step)); // kerb lane first','const each = rightLanes(n,step); // inner lane first, offsets left to right')
    patch(f,"const leftOf = (lanes) => {\n    const keep = lanes.length > 1 ? (lanes[1] - lanes[0]) / 2 : 1.65;\n    return lanes.map((x) => x - lanes[lanes.length - 1] - keep);\n  };","const leftOf = rightOf; // shared centreline: positive right-hand offsets")
    # Preserve true divided-carriageway side: merge only geometrically right-hand pairs.
    patch(f,'const offset = offsetOf(e, f);','const offset = offsetOf(e, f);\n          if(offset>0.25 || offsetOf(f,e)>0.25) continue; // opposing carriageway must be left of travel')
    f=out/'js/road-paint.js'
    patch(f,"import * as THREE from 'three/webgpu';","import * as THREE from 'three/webgpu';\nimport { stopBand } from './traffic-side.mjs';")
    patch(f,"const right = back ? Math.min(f.half - 0.1, f.lanes[f.lanes.length - 1] + 1.8) : f.half - 0.1;","const [left,right] = stopBand(f,!!back);")
    patch(f,"if (node.signal) across(f, f.len - 0.35, -f.half + 0.1, right, 0.45, WHITE);","if (node.signal) across(f, f.len - 0.35, left, right, 0.45, WHITE);")
    patch(f,"across(f, s, -f.half + 0.1, right, 0.2, WHITE, 0.6, 0.5);","across(f, s, left, right, 0.2, WHITE, 0.6, 0.5);")
    patch(f,"if (e.axis === 'ave') for (const o of half ? [-e.half + 0.4] : [-e.half + 0.4, e.half - 0.4]) along(e, o, 0.1, YELLOW);","if (e.axis === 'ave') for (const o of half ? [e.half - 0.4] : [-e.half + 0.4, e.half - 0.4]) along(e, o, 0.1, WHITE);")
    if a.traffic_preview:
        # Record actual emitted paint triangles, not a second simulated marking.
        patch(f,'const lines = [];',"""const lines = [];
  const marks=[];
  const edgeInfo=e=>({id:e.id??null,from:[e.from.x,e.from.z],to:[e.to.x,e.to.z],
    x0:e.x0,z0:e.z0,dx:e.dx,dz:e.dz,rx:e.rx,rz:e.rz,len:e.len,half:e.half,
    lanes:[...e.lanes],shared:e.divided||e.centred===false});""")
        patch(f,'strip(ax, az, bx, bz, w, col, period, duty, 0, 1, liftOf(e, fa, fa));',"""const first=index.length;
    strip(ax, az, bx, bz, w, col, period, duty, 0, 1, liftOf(e, fa, fa));
    marks.push({kind:w<.5&&s>=e.len-1&&s<=e.len?'stop':'crossing',edge:edgeInfo(e),
      s,o0,o1,width:w,color:col.getHex(),first,count:index.length-first});""")
        patch(f,'strip(ax, az, bx, bz, line.w, line.col, line.period, line.duty, line.phase, line.flow,\n        liftOf(line.e, fraction(line.e, ax, az), fraction(line.e, bx, bz)));',"""const first=index.length;
      strip(ax, az, bx, bz, line.w, line.col, line.period, line.duty, line.phase, line.flow,
        liftOf(line.e, fraction(line.e, ax, az), fraction(line.e, bx, bz)));
      marks.push({kind:'longitudinal',edge:edgeInfo(line.e),offset:line.o,
        endpoints:line.ends,width:line.w,color:line.col.getHex(),first,count:index.length-first});""")
        patch(f,"mesh.name = 'RoadMarkings';","mesh.name = 'RoadMarkings';\n  mesh.userData.trafficMarks=marks;")
    f=out/'js/traffic.js'
    patch(f,"const ACROSS = 'R';","import { ACROSS } from './traffic-side.mjs';")
    f=out/'js/controllers.js'; patch(f,'if (l.name !== name) continue;',"if (name && l.name !== name) continue;\n    if (l.tunnel || l.bridge || (l.layer || 0) !== 0 || !['residential','unclassified','tertiary','secondary','living_street'].includes(l.kind)) continue;")
    patch(f,'const len = Math.hypot(best.dx, best.dz);',"if (!best && name) return roadSpawn(null, x, z);\n  if (!best) throw new Error('No surface road for spawn');\n  const len = Math.hypot(best.dx, best.dz);")
    patch(f,"import { GEO } from './nairobi-geodata.js';","import { GEO } from './nairobi-geodata.js';\nimport { directedSpawn } from './traffic-side.mjs';")
    patch(f,"const fx = best.dx / len, fz = best.dz / len;\n  // Kenya drives on the left: on a two-way road, half a lane's width left of the centre line\n  const off = best.l.oneway ? -best.l.w / 4 : best.l.w / 4;\n  return [best.x + fz * off, best.z - fx * off, Math.atan2(fx, fz), fz, -fx];","return directedSpawn(best.x,best.z,best.dx,best.dz,best.l.w,best.l.oneway);")
    patch(f,"const SPAWN = roadSpawn('Kenyatta Avenue', -110, -505);","const SPAWN = roadSpawn(null, 0, 0);")
    patch(f,'const [x, z] = [-560, 80];','const [x, z] = [SPAWN[0], SPAWN[1]];')
    f=out/'js/city-config.js'; patch(f,"if (SHORT[l.name]) out.push({ name: l.name === 'Uhuru park' ? 'Uhuru Park' : l.name, short: SHORT[l.name], x: l.x, z: l.z });","out.push({ name: l.name, short: l.name, x: l.x, z: l.z });")
    patch(f,"place || roads || 'Nairobi'","place || roads || 'Pedome'")
    s=f.read_text(); s,n=re.subn(r'const TELEPORT_LOCATIONS = Object\.fromEntries\(\[.*?\]\s*\.map\(.*?\)\);',"const TELEPORT_LOCATIONS = {};",s,count=1,flags=re.S); assert n==1; f.write_text(s,encoding='utf-8')
    shutil.copy2(P(__file__).resolve().parent/'pedome-ui.js',out/'js/pedome-ui.js')
    # Minimal world shell keeps upstream rendering, steering, chase camera and collision routines; no Kenya traffic.
    shutil.copy2(P(__file__).resolve().parent/'pedome-render-diagnostics.mjs',out/'js/pedome-render-diagnostics.mjs')
    f=out/'js/ground.js'
    # Preserve painting coordinates while resampling the final texture to power-of-two dimensions.
    patch(f,"import * as THREE from 'three/webgpu';","import * as THREE from 'three/webgpu';\nimport { configureGroundTexture } from './pedome-render-diagnostics.mjs';")
    patch(f,"  map.anisotropy = renderer.getMaxAnisotropy ? renderer.getMaxAnisotropy() : 8;","  configureGroundTexture(map,renderer);")
    patch(f,"const map = new THREE.CanvasTexture(paintMap());","const painted=paintMap(); const pot=document.createElement(\'canvas\'); pot.width=painted.width; pot.height=2**Math.round(Math.log2(painted.height)); pot.getContext(\'2d\').drawImage(painted,0,0,pot.width,pot.height); const map = new THREE.CanvasTexture(pot);")
    (out/'js/pedome.js').write_text('''import * as THREE from 'three/webgpu';
import { GEO } from './nairobi-geodata.js';
import { buildGround } from './ground.js';
import { buildBuildings } from './buildings.js';
import { buildBridges } from './bridges.js';
import { buildStreets } from './streets.js';
import { buildRoadNetwork } from './road-network.js';
import { buildColliders } from './colliders.js';
import { ThirdPersonControllerManager, roadSpawn } from './controllers.js';
import { CameraSystem } from './cameras.js';
import { GamepadControls } from './gamepad-controls.js';
import { installPedomeUI } from './pedome-ui.js';
import { rendererOptions,installRenderDiagnostics,improveDepth } from './pedome-render-diagnostics.mjs';
const status=document.querySelector('#status');
try {
 const renderer=new THREE.WebGPURenderer(rendererOptions());
 renderer.setPixelRatio(Math.min(devicePixelRatio,1.5)); renderer.setSize(innerWidth,innerHeight); document.body.append(renderer.domElement); await renderer.init();const renderDiagnostics=await installRenderDiagnostics(renderer);
 const scene=new THREE.Scene(); scene.background=new THREE.Color(0xb8d4ef); scene.fog=new THREE.Fog(0xb8d4ef,350,1100);
 scene.add(new THREE.HemisphereLight(0xffffff,0x77805d,2.2)); const sun=new THREE.DirectionalLight(0xfff0d8,2.4); sun.position.set(90,140,50); scene.add(sun);
 scene.add(buildGround(renderer)); scene.add(await buildBuildings()); const bridges=buildBridges(); scene.add(bridges);
 const world=buildColliders(bridges.userData.piers); const network=buildRoadNetwork(); buildStreets(scene,network,[]);
 const controllers=new ThirdPersonControllerManager(scene,world); const cameras=new CameraSystem(renderer.domElement,controllers); const camera=cameras.camera;improveDepth(camera,scene); const gamepad=new GamepadControls(controllers,cameras);
 /* P0 renders directly, without upstream screen-space reflection MRT buffers. */
 scene.traverse(o=>{for(const mat of (Array.isArray(o.material)?o.material:[o.material]))if(mat?.mrtNode){mat.mrtNode=null;mat.needsUpdate=true;}});
 window.mapslop={GEO,controllers,camera,world};window.mapslop.renderDebug=()=>renderDiagnostics(scene,window.mapslop.orthoPreview?.ortho,camera); const spawn=roadSpawn(null,0,0); controllers.teleportActiveTo(spawn[0],spawn[1],spawn[2]); const ui=installPedomeUI(GEO,controllers,spawn,cameras);
 window.addEventListener('keydown',e=>{if(e.code==='KeyR')controllers.teleportActiveTo(spawn[0],spawn[1],spawn[2]);});
 window.addEventListener('resize',()=>{renderer.setSize(innerWidth,innerHeight); camera.aspect=innerWidth/innerHeight; camera.updateProjectionMatrix();});
 let last=performance.now(); renderer.setAnimationLoop(now=>{const dt=Math.max(0,Math.min(.05,(now-last)/1000));last=now;gamepad.update(dt);controllers.update(dt,now/1000); cameras.update(dt,now/1000);renderer.render(scene,camera);ui.update(now);status.textContent=(GEO.frame.testFixture?'TESTE FICTÍCIO — ':GEO.frame.flatTerrain?'PEDOME — relevo plano — ':GEO.frame.demSource==='SYNTHETIC TEST TERRAIN'?'PEDOME — terreno de teste — ':'PEDOME — ')+Math.round(Math.abs(controllers.getActiveEntity().speed)*3.6)+' km/h'; window.mapslop.ready=true;});
} catch(e){status.textContent='Erro: '+e.message; console.error(e);throw e;}
''',encoding='utf-8')
    if a.roof_preview:
        f=out/'js/pedome.js'
        patch(f,"import { buildBuildings } from './buildings.js';","import { buildDetailedBuildings as buildBuildings } from './pedome-buildings-detail.mjs';")
        patch(f,'scene.add(await buildBuildings());','const buildingGroup=await buildBuildings(); scene.add(buildingGroup); window.buildingDetailReport=buildingGroup.userData.buildingDetailReport;')
    if a.traffic_preview:
        if a.fixture or not a.terrain_bin or a.roof_preview:
            p.error('--traffic-preview requires real binary terrain, without other previews')
        f=out/'js/pedome.js'
        patch(f,'window.mapslop={GEO,controllers,camera,world};','window.mapslop={GEO,controllers,camera,world,trafficPreview:{network,scene,renderer,roadSpawn,getUI:()=>ui}};')
    html=(out/'index.html').read_text(); imp=re.search(r'<script type="importmap">.*?</script>',html,re.S).group()
    if a.three_vendor:
        shutil.copytree(a.three_vendor,out/'vendor/three')
        imp=re.sub(r'https://cdn\.jsdelivr\.net/gh/mrdoob/three\.js@[^/]+/', './vendor/three/',imp)
    (out/'index.html').write_text('''<!doctype html><html lang="pt"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MapSlop | Pedome P0</title>'''+imp+'''<style>html,body{margin:0;overflow:hidden;background:#202b36;font:15px system-ui;color:#fff}canvas{display:block}#status,#credits{position:fixed;z-index:1;background:#15202bdc;padding:10px;border-radius:6px;left:10px}#status{top:10px}#credits{bottom:10px;font-size:12px}a{color:white}</style><div id="status">A construir mapa…</div><div id="credits">MapSlop P0 · <a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a> · Slop Nairobi / Mr.doob · Copernicus (quando usado)</div><script type="module" src="./js/pedome.js"></script></html>''',encoding='utf-8')
    if terrain:
        page=out/'index.html'; page.write_text(page.read_text(encoding='utf-8').replace('Copernicus (quando usado)', 'DGT — MDT 0,5 m (uso experimental)' if terrain['source'].startswith('DGT') else 'Terreno sintético de teste'),encoding='utf-8')
    write(out/'build-report.json',dict(fixture=a.fixture,flat=geo['frame']['flatTerrain'],terrainSource=geo['frame']['demSource'],terrainCell=geo['terrain']['cell'],terrainKind=geo['terrain'].get('kind','grid'),bbox=BBOX,roads=len(geo['roads']),buildings=len(geo['buildings']),nodes=len(geo['roadGraph']['nodes']),links=len(geo['roadGraph']['links']),estimatedBuildings=sum(b.get('est',0) for b in geo['buildings'])))
    shutil.copytree(src/'tests',out/'tests')
    # Update only the stub fixture, not controller assertions.
    testfile=out/'tests/controllers.test.cjs'; patch(testfile,"name: 'Kenyatta Avenue', oneway:","name: 'TESTE', kind: 'residential', oneway:")
    patch(testfile,"'./nairobi-geodata.js': { GEO }","'./nairobi-geodata.js': { GEO },\n      './traffic-side.mjs': loadModule(readFileSync(join(__dirname, '../js/traffic-side.mjs'), 'utf8'))")
    shutil.copy2(P(__file__).resolve().parent.parent/'tests'/'right-hand-traffic.test.cjs',out/'tests/right-hand-traffic.test.cjs')
    run('npm.cmd' if __import__('os').name=='nt' else 'npm','test',cwd=out)
    run('node','--input-type=module','-e',"import {buildRoadNetwork} from './js/road-network.js'; import {layoutStreets,streetSoups} from './js/street-geometry.js'; const net=buildRoadNetwork(); const l=layoutStreets(net.streets); const s=streetSoups(l); if(!s.asphalt.index.length) throw Error('No road geometry'); console.log('Road geometry:',net.streets.edges.length,'edges',s.asphalt.index.length/3,'triangles');",cwd=out)
    print('BUILD:',out, (out/'build-report.json').read_text()); print('Serve: python -m http.server 8080 --directory',out)
if __name__=='__main__': main()
