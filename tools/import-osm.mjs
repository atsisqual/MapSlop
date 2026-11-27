#!/usr/bin/env node
// MapSlop — geographic import, Node.js 18+. OSM data: ODbL.
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const args = process.argv.slice(2);
const opt = (name, fallback) => {
  const i = args.indexOf(name);
  if (i < 0) return fallback;
  if (!args[i+1] || args[i+1].startsWith('--')) throw Error('Missing value for '+name);
  return args[i+1];
};
const bbox = opt('--bbox','41.4110,-8.3929,41.4200,-8.3809').split(',').map(Number);
if (bbox.length !== 4 || !bbox.every(Number.isFinite) ||
    bbox[0] >= bbox[2] || bbox[1] >= bbox[3] ||
    bbox[0] < -90 || bbox[2] > 90 || bbox[1] < -180 || bbox[3] > 180 ||
    bbox[2]-bbox[0] > .1 || bbox[3]-bbox[1] > .1) throw Error('Invalid or oversized bbox (S,W,N,E)');
const name = opt('--name','pedome');
if (!/^[a-z0-9-]+$/.test(name)) throw Error('Invalid map name');
const dir = resolve(opt('--out','data/'+name));
const b = bbox.join(',');
const query = '[out:json][timeout:90];(way["highway"]('+b+');way["building"]('+b+');relation["building"]('+b+');node["natural"="tree"]('+b+');nwr["amenity"]('+b+');nwr["shop"]('+b+');way["waterway"]('+b+');way["natural"="water"]('+b+');relation["natural"="water"]('+b+'););out body geom;';
const input = opt('--input',null);
const endpoint = opt('--endpoint','https://overpass-api.de/api/interpreter');
let raw;
if (input) {
  raw = JSON.parse(await readFile(input,'utf8'));
} else {
  const res = await fetch(endpoint,{method:'POST',body:new URLSearchParams({data:query}),signal:AbortSignal.timeout(120000)});
  if (!res.ok) throw Error('Overpass HTTP '+res.status+'; retry later or supply --input');
  raw = await res.json();
}
if (!Array.isArray(raw.elements) || raw.remark) throw Error('Invalid or partial Overpass response: '+(raw.remark||'missing elements'));
const origin = [(bbox[0]+bbox[2])/2,(bbox[1]+bbox[3])/2];
const metersPerDeg = Math.PI*6378137/180;
const local = (p) => [(p.lon-origin[1])*metersPerDeg*Math.cos(origin[0]*Math.PI/180), -(p.lat-origin[0])*metersPerDeg];
const roads = [];
for (const e of raw.elements) {
  if (e.type !== 'way' || !e.tags?.highway || !Array.isArray(e.geometry) || e.geometry.length < 2) continue;
  if (!Array.isArray(e.nodes) || e.nodes.length !== e.geometry.length || e.geometry.some(p=>!p||!Number.isFinite(p.lat)||!Number.isFinite(p.lon))) continue;
  roads.push({id:e.id, tags:e.tags, nodes:e.nodes, points:e.geometry.map(local)});
}
const stats = {
  map:name, bbox, origin, projection:'local equirectangular metres; x east, z south',
  attribution:'© OpenStreetMap contributors — ODbL 1.0',
  sourceTimestamp:raw.osm3s?.timestamp_osm_base??null,
  roadWays:roads.length,
  buildingWays:raw.elements.filter(e=>e.type==='way'&&e.tags?.building).length,
  buildingRelations:raw.elements.filter(e=>e.type==='relation'&&e.tags?.building).length,
  trees:raw.elements.filter(e=>e.type==='node'&&e.tags?.natural==='tree').length,
  amenities:raw.elements.filter(e=>e.tags?.amenity).length,
  shops:raw.elements.filter(e=>e.tags?.shop).length
};
await mkdir(dir,{recursive:true});
await Promise.all([
  writeFile(resolve(dir,'osm.json'),JSON.stringify(raw)),
  writeFile(resolve(dir,'roads.json'),JSON.stringify({origin,roads})),
  writeFile(resolve(dir,'summary.json'),JSON.stringify(stats,null,2)+'\n')
]);
console.log(JSON.stringify(stats,null,2));
