const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const test=require('node:test');
const {loadModule}=require('./helpers/module.cjs');
const source=name=>readFileSync(join(__dirname,'../js',name),'utf8');
const policy=loadModule(source('traffic-side.mjs'));
const points=[[-80,-80],[0,-80],[80,-80],[-80,0],[0,0],[80,0],[-80,80],[0,80],[80,80],
  [160,-30],[160,30],[220,30],[220,-30]];
const nodes=points.map(([x,z])=>({x,z}));
const links=[];
function add(a,b,oneway=0,roundabout=0,kind='residential',w=7.6,lanes=2){
  links.push({a,b,way:links.length+1,pts:[...points[a],...points[b]],kind,w,lanes,oneway,roundabout});
}
// Grid with two four-arm junctions (centre and approach to ring); retain loops.
for(const [a,b] of [[0,1],[1,2],[3,4],[4,5],[6,7],[7,8],[0,3],[3,6],[1,4],[4,7],[2,5],[5,8]])add(a,b);
add(5,9,1,0,'residential',4.3,1);
add(10,8,-1,0,'residential',4.3,1); // legal direction 8 -> 10
// Counter-clockwise geographic rotation: negative signed area in x,z.
for(const [a,b] of [[9,10],[10,11],[11,12],[12,9]])add(a,b,1,1,'residential',4.3,1);
add(12,2);
const GEO={roadGraph:{nodes,links}};
const {buildRoadNetwork}=loadModule(source('road-network.js'),{imports:{
 './nairobi-geodata.js':{GEO},
 './city-config.js':{SIGNAL_TIMING:{cycle:60,mainRed:30}},
 './elevation.js':{nodeLift:new Float32Array(nodes.length),liftAlong:()=>0,liftBreaks:()=>[]},
 './traffic-side.mjs':policy
}});
const network=buildRoadNetwork();
function same(p,n){return Math.hypot(p.x-n[0],p.z-n[1])<.01;}
function edge(a,b){return network.paintEdges.find(e=>same(e.from,points[a])&&same(e.to,points[b]));}
test('both directions keep right at two junctions',()=>{
  for(const [a,b] of [[1,4],[4,1],[3,4],[4,5],[2,5],[5,2]]){
    const e=edge(a,b);assert.ok(e,'missing direction '+a+' '+b);
    assert.ok(e.lanes.every(o=>o>0));
    assert.ok(e.lanes.every((o,i)=>!i||o>e.lanes[i-1]));
    assert.ok(e.lanes.every(o=>o<e.half));
  }
  assert.ok(network.edges.length>0);
  const junctions=network.nodes.filter(n=>same(n,points[4])||same(n,points[5]));
  assert.equal(junctions.length,2);
  for(const n of junctions)for(const e of n.in)for(const m of e.moves){
    const cross=e.dx*m.to.dz-e.dz*m.to.dx;
    assert.equal(m.turn,cross>.5?'R':cross<-.5?'L':'S');
    assert.ok(m.to!==e.opposite);
  }
});
test('one-way and reverse-one-way are centred, never reverse direction',()=>{
  for(const [a,b] of [[5,9],[8,10]]){
    const e=edge(a,b);assert.ok(e);
    assert.equal(edge(b,a),undefined);
    assert.ok(e.lanes.every(o=>Math.abs(o)<.001));
  }
});
test('ring keeps mapped counter-clockwise direction and centred lanes',()=>{
  for(const [a,b] of [[9,10],[10,11],[11,12],[12,9]]){
    assert.ok(edge(a,b));assert.equal(edge(b,a),undefined);
    assert.ok(edge(a,b).lanes.every(o=>Math.abs(o)<.001));
  }
  const ringNodes=network.nodes.filter(n=>[9,10,11,12].some(i=>same(n,points[i])));
  assert.ok(ringNodes.length>=3);
  for(const n of ringNodes)if(n.arms.some(a=>a.ring))assert.ok(n.arms.filter(a=>a.ring).every(a=>a.group===0));
});
test('right-hand stop/give-way paint is only on arriving half',()=>{
  const f=edge(1,4),back=edge(4,1);
  const [lo,hi]=policy.stopBand(f,!!back);
  assert.ok(lo>=0&&hi>lo&&hi<f.half);
  const [a,b]=policy.stopBand(edge(5,9),false);
  assert.ok(a<0&&b>0);
  assert.equal(policy.ACROSS,'L');
  assert.match(source('road-paint.js'),/stopBand\(f,!!back\)/);
  assert.match(source('traffic.js'),/import \{ ACROSS \} from '\.\/traffic-side\.mjs'/);
});
test('spawn right of travel in four cardinal directions and respects reverse oneway',()=>{
  for(const [dx,dz] of [[1,0],[-1,0],[0,1],[0,-1]]){
    const [x,z,h]=policy.directedSpawn(0,0,dx,dz,8,0);
    assert.ok(Math.abs(x*(-dz)+z*dx-2)<1e-9);
    assert.ok(Math.abs(Math.sin(h)-dx)<1e-9&&Math.abs(Math.cos(h)-dz)<1e-9);
  }
  const [x,z,h]=policy.directedSpawn(0,0,1,0,8,-1);
  assert.equal(x,0);assert.equal(z,0);assert.ok(Math.sin(h)<-.999);
  assert.match(source('controllers.js'),/return directedSpawn\(best\.x/);
});
