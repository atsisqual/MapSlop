#!/usr/bin/env python3
import json
import sys
from pathlib import Path
import numpy as np

def annotate(root):
    profiles=root/'road-profiles.json'
    if not profiles.exists():return
    p=json.loads(profiles.read_text());xy=np.array(p['xy']);ys=np.array(p['height_m'])
    nodes={int(i):int(n) for i,n in p['junction_nodes'].items()}
    radii={i:max(w['width_m']/2 for w in p['ways'] if i in w['ids']) for i in nodes.values()}
    for group in p.get('platform_group_details',[]):
        for i,r in zip(group['node_indices'],group['radius_m']):radii[int(i)]=float(r)
    ramp_byway={}
    for row in p.get('ramp_sections',[]):ramp_byway.setdefault(row['way'],[]).append(row)
    byway={}
    for w in p['ways']:byway.setdefault(w['way'],[]).append(w)
    for mode in ('baseline','regression','previous','carved'):
        path=root/mode/'browser-report.json'
        if not path.exists():continue
        r=json.loads(path.read_text());d=r.get('longDrive',{});v=d.get('vertical_metrics',{})
        for name,metric in v.items():
            if not isinstance(metric,dict):continue
            for peak in metric.get('peaks',[]):
                q=np.array([peak['x_m'],peak['z_m']])
                best=None
                for w in byway.get(peak['way'],[]):
                    for k,(a,b) in enumerate(zip(w['ids'],w['ids'][1:])):
                        delta=xy[b]-xy[a];t=float(np.clip(np.dot(q-xy[a],delta)/np.dot(delta,delta),0,1))
                        dist=float(np.linalg.norm(q-xy[a]-t*delta))
                        item=(dist,k,t,w,a,b)
                        if best is None or dist<best[0]:best=item
                if best:
                    dist,k,t,w,a,b=best
                    peak.update(way_station_m=w['s'][k]+t*(w['s'][k+1]-w['s'][k]),way_segment_index=k,
                                distance_to_axis_m=dist,reference_profile_y_m=float(ys[a]+t*(ys[b]-ys[a])))
                if best and mode=='carved':
                    stations=ramp_byway.get(peak['way'],[])
                    matching=[row for row in stations if np.linalg.norm(np.asarray(row['start_xz'])-xy[w['ids'][0]])<.01]
                    ramp_list=[r for row in matching for r in row['ramps']]
                    if ramp_list:
                        s=peak['way_station_m']
                        nearest_ramp=min(ramp_list,key=lambda r: min(abs(s-r['start_m']),abs(s-r['end_m'])))
                        a,b=nearest_ramp['start_m'],nearest_ramp['end_m']
                        peak['nearest_ramp']=nearest_ramp
                        peak['ramp_signed_distance_m']=-min(s-a,b-s) if a<=s<=b else min(abs(s-a),abs(s-b))
                if nodes:
                    nearest=min(nodes,key=lambda n:np.linalg.norm(q-xy[nodes[n]]))
                    idx=nodes[nearest];dist=float(np.linalg.norm(q-xy[idx]))
                    nearest_edge=min(nodes,key=lambda n:abs(float(np.linalg.norm(q-xy[nodes[n]]))-radii[nodes[n]]))
                    edgeidx=nodes[nearest_edge]
                    edge=float(np.linalg.norm(q-xy[edgeidx])-radii[edgeidx])
                    peak.update(nearest_osm_junction=nearest,junction_distance_m=dist,
                                nearest_platform_edge_osm_node=nearest_edge,platform_edge_signed_distance_m=edge,
                                platform_height_m=float(ys[edgeidx]))
                peak['collision_surface_minus_tin_m']=peak['ground']-peak['terrain']
        path.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
        print('DRIVE_PEAKS',mode,json.dumps({k:v[k].get('peaks',[])[:10] for k in ('surface_raw','surface_window_0_2s','terrain_raw','terrain_window_0_2s') if k in v},allow_nan=False),flush=True)
if __name__=='__main__':annotate(Path(sys.argv[1]))
