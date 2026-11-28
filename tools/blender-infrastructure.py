#!/usr/bin/env python3
"""Execute original Blender infrastructure add-ons offline on a bounded OSM file.
Exports candidate GLB and per-object inventory; deliberately no terrain/physics integration.
Requires pinned upstream checkout and compatible bpy environment.
"""
import argparse,hashlib,importlib.util,json,math,socket,sys
from pathlib import Path
import bpy,addon_utils
from mathutils import Vector
def main():
    p=argparse.ArgumentParser();p.add_argument("backend",choices=["mosaiq","junction"]);p.add_argument("addon",type=Path);p.add_argument("osm",type=Path);p.add_argument("output",type=Path);p.add_argument("--bounds",nargs=4,type=float,required=True);p.add_argument("--input-sha256",required=True);a=p.parse_args()
    if hashlib.sha256(a.osm.read_bytes()).hexdigest()!=a.input_sha256:raise ValueError("Input hash mismatch")
    a.output.mkdir(parents=True,exist_ok=False);r={"pass":False,"backend":a.backend,"blender":bpy.app.version_string,"input_sha256":a.input_sha256,"bounds_lon_lat":a.bounds}
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        def denied(*a,**k):raise RuntimeError("Network forbidden")
        socket.socket.connect=denied;socket.socket.connect_ex=denied;socket.create_connection=denied
        if a.backend=="mosaiq":
            assert a.addon.name=="mosaiq_osm_vr"
            sys.path.insert(0,str(a.addon.parent.resolve()))
            addon_utils.enable(a.addon.name,default_set=True,persistent=False)
            assert addon_utils.check(a.addon.name)[1]
            props=bpy.context.scene.osm_bbox_props
            props.minlon,props.minlat,props.maxlon,props.maxlat=a.bounds
            props.origin_shift=True;props.import_roads=True;props.import_pois=False
            result=bpy.ops.osm_bbox.import_pbf('EXEC_DEFAULT',filepath=str(a.osm.resolve()))
            assert 'FINISHED' in result,result
            r["projection"]="Web Mercator with SW origin shift; NOT metric ground scale at this latitude"
            r["poi_status"]="disabled; no licensed prefabs supplied"
        else:
            spec=importlib.util.spec_from_file_location("osm_intersections",a.addon/"osm_intersections.py")
            mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
            opts=mod.Options(left_hand_traffic=False,infer_grass_verges=False,sidewalk_width=1.5)
            r["upstream_stats"]=mod.generate_scene_from_osm(bpy.context,str(a.osm.resolve()),opts)
            assert r["upstream_stats"]["road_meshes"]>0
            assert r["upstream_stats"]["junctions"]>0
            r["projection"]="upstream local projection; independent alignment required"
        bpy.context.view_layer.update()
        rows=[]
        for o in bpy.context.scene.objects:
            if o.type!="MESH":continue
            o.data.calc_loop_triangles()
            if not o.data.loop_triangles:continue
            points=[o.matrix_world@Vector(v) for v in o.bound_box]
            bounds=[[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]]
            if not all(math.isfinite(v) for b in bounds for v in b):raise ValueError("Nonfinite bounds")
            rows.append({"name":o.name,"triangles":len(o.data.loop_triangles),"bounds_blender_xyz":bounds,"materials":[m.name for m in o.data.materials if m],"osm_id":o.get("osm_id")})
        assert rows and sum(x["triangles"] for x in rows)>10
        dest=a.output/"candidate.glb";result=bpy.ops.export_scene.gltf(filepath=str(dest),export_format="GLB",export_yup=True)
        assert 'FINISHED' in result and dest.stat().st_size>0
        r.update(pass_=True,objects=rows,mesh_count=len(rows),triangles=sum(x["triangles"] for x in rows),glb_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),glb_bytes=dest.stat().st_size)
        r["pass"]=r.pop("pass_")
    finally:
        (a.output/"report.json").write_text(json.dumps(r,indent=2)+"\n")
    print("BLENDER_INFRA",json.dumps({k:v for k,v in r.items() if k!="objects"}))
if __name__=="__main__":main()
