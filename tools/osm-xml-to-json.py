#!/usr/bin/env python3
"""Convert a complete OSM map XML export to Overpass-style geometry without user metadata."""
import argparse, json, xml.etree.ElementTree as ET
from pathlib import Path

def convert(src, dst, bbox):
    root=ET.parse(src).getroot()
    if root.tag!='osm': raise ValueError('Expected OSM XML')
    s,w,n,e=bbox
    bounds=root.find('bounds')
    if bounds is not None and not (float(bounds.get('minlat'))<=s and float(bounds.get('minlon'))<=w and float(bounds.get('maxlat'))>=n and float(bounds.get('maxlon'))>=e): raise ValueError('Export does not cover pilot bounds')
    def tags(x): return {t.get('k'):t.get('v') for t in x.findall('tag')}
    nodes={int(x.get('id')):{'lat':float(x.get('lat')),'lon':float(x.get('lon'))} for x in root.findall('node')}
    def inside(p): return s<=p['lat']<=n and w<=p['lon']<=e
    def touches(ps):
        return bool(ps) and min(p['lat'] for p in ps)<=n and max(p['lat'] for p in ps)>=s and min(p['lon'] for p in ps)<=e and max(p['lon'] for p in ps)>=w
    ways={}; missing=0
    for x in root.findall('way'):
        i=int(x.get('id')); ids=[int(t.get('ref')) for t in x.findall('nd')]; t=tags(x)
        if any(j not in nodes for j in ids): missing+=1; continue
        ways[i]={'type':'way','id':i,'nodes':ids,'geometry':[nodes[j] for j in ids],'tags':t}
    elements=[{'type':'node','id':int(x.get('id')),**nodes[int(x.get('id'))],'tags':tags(x)} for x in root.findall('node') if x.find('tag') is not None and inside(nodes[int(x.get('id'))])]
    elements += [x for x in ways.values() if x['tags'] and touches(x['geometry'])]
    skipped=0
    for x in root.findall('relation'):
        t=tags(x)
        if not any(k in t for k in ['building','building:part','landuse','natural','leisure','amenity','tourism','historic']) and t.get('type')!='building': continue
        members=[]; incomplete=False
        for m in x.findall('member'):
            k=m.get('type'); i=int(m.get('ref')); member={'type':k,'ref':i,'role':m.get('role','')}
            if k=='way' and i in ways: member['geometry']=ways[i]['geometry']
            elif k=='node' and i in nodes: member.update(nodes[i])
            else: incomplete=True
            members.append(member)
        if not any(touches(m.get('geometry',[])) for m in members): continue
        if incomplete: skipped+=1; continue
        elements.append({'type':'relation','id':int(x.get('id')),'tags':t,'members':members})
    result={'version':0.6,'generator':'MapSlop XML converter','copyright':'OpenStreetMap contributors, ODbL 1.0','elements':elements}
    Path(dst).write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print('converted',len(elements),'elements; incomplete ways',missing,'incomplete relevant relations',skipped)
    print('highway ways',sum(x['type']=='way' and 'highway' in x['tags'] for x in elements),'building ways',sum(x['type']=='way' and 'building' in x['tags'] for x in elements))
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('src');p.add_argument('dst');p.add_argument('--bbox',nargs=4,type=float,default=(41.4105,-8.395,41.4195,-8.383));a=p.parse_args();convert(a.src,a.dst,a.bbox)
