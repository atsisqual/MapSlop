#!/usr/bin/env python3
"""Offline bake of evaluated Blender Geometry Nodes to GLB.
Generic converter; does not include or emulate MRoadGen's node graph.
Use only reviewed, self-contained .blend assets in an isolated environment.
"""
import argparse,hashlib,json,math,socket,sys
from pathlib import Path
import bpy
from mathutils import Vector

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return h.hexdigest()

def fixture(path):
    if path.exists():raise ValueError("Refuse overwrite")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mesh=bpy.data.meshes.new("Road strip source")
    mesh.from_pydata([(0,0,0),(5,0,0),(5,3,0),(0,3,0)],[],[(0,1,2,3)]);mesh.update()
    obj=bpy.data.objects.new("Synthetic road strip",mesh);bpy.context.collection.objects.link(obj)
    mat=bpy.data.materials.new("Synthetic asphalt");mat.use_nodes=True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(.14,.14,.14,1)
    mesh.materials.append(mat)
    group=bpy.data.node_groups.new("QA road geometry","GeometryNodeTree")
    group.interface.new_socket(name="Geometry",in_out="INPUT",socket_type="NodeSocketGeometry")
    group.interface.new_socket(name="Geometry",in_out="OUTPUT",socket_type="NodeSocketGeometry")
    i=group.nodes.new("NodeGroupInput");o=group.nodes.new("NodeGroupOutput")
    extrude=group.nodes.new("GeometryNodeExtrudeMesh");extrude.mode="FACES"
    extrude.inputs["Offset Scale"].default_value=.2
    extrude.inputs["Individual"].default_value=False
    group.links.new(i.outputs["Geometry"],extrude.inputs["Mesh"]);group.links.new(extrude.outputs["Mesh"],o.inputs["Geometry"])
    mod=obj.modifiers.new("Procedural road thickness","NODES");mod.node_group=group
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    print("BLEND_FIXTURE",sha(path))

def bake(source,out,expected,collection=None):
    if source.suffix.lower()!=".blend" or sha(source)!=expected:raise ValueError("Unverified .blend")
    out.mkdir(parents=True,exist_ok=False)
    report={"pass":False,"source_sha256":expected,"blender":bpy.app.version_string,"collection":collection}
    def save():(out/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    try:
        def denied(*a,**k):raise RuntimeError("Network forbidden")
        socket.socket.connect=denied;socket.socket.connect_ex=denied;socket.create_connection=denied
        bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
        if bpy.data.libraries:raise ValueError("External linked libraries not supported")
        for im in bpy.data.images:
            if im.source in {"MOVIE","SEQUENCE","TILED"}:raise ValueError("Unsupported external image sequence/UDIM")
            if im.source=="FILE" and not im.packed_file:raise ValueError("Pack image dependencies before baking: "+im.name)
        deps=bpy.context.evaluated_depsgraph_get()
        if collection:
            col=bpy.data.collections.get(collection)
            if col is None:raise ValueError("Unknown collection")
            objs=list(col.all_objects)
        else:objs=list(bpy.context.scene.objects)
        sources=[o for o in objs if o.type in {"MESH","CURVE","SURFACE"} and not o.hide_render and not o.hide_get()]
        if not sources:raise ValueError("No visible mesh/curve sources")
        if any(x.is_instance for x in deps.object_instances):raise ValueError("Realize geometry-node/collection instances before export")
        baked=[];rows=[]
        for original in sources:
            ev=original.evaluated_get(deps)
            mesh=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=deps)
            if mesh is None or not len(mesh.polygons):continue
            mesh.calc_loop_triangles()
            points=[ev.matrix_world@v.co for v in mesh.vertices]
            bounds=[[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]]
            if not all(math.isfinite(x) and abs(x)<=100000 for b in bounds for x in b):raise ValueError("Invalid or nonlocal bounds")
            rows.append({"source":original.name,"input_triangles":sum(max(0,len(p.vertices)-2) for p in original.data.polygons) if original.type=="MESH" else None,"evaluated_triangles":len(mesh.loop_triangles),"geometry_nodes":sum(m.type=="NODES" for m in original.modifiers),"bounds_blender_xyz":bounds,"materials":[m.name for m in mesh.materials if m]})
            baked.append((original.name,mesh,ev.matrix_world.copy()))
        if not baked or sum(r["evaluated_triangles"] for r in rows)>2_000_000:raise ValueError("Empty or over-budget scene")
        # Export only new evaluated meshes, never source curves, terrain or hidden helpers.
        bpy.ops.object.select_all(action="DESELECT")
        for name,mesh,mat in baked:
            obj=bpy.data.objects.new("Baked "+name,mesh);bpy.context.collection.objects.link(obj);obj.matrix_world=mat;obj.select_set(True)
        dest=out/"baked.glb"
        res=bpy.ops.export_scene.gltf(filepath=str(dest),export_format="GLB",export_yup=True,use_selection=True)
        if "FINISHED" not in res or dest.stat().st_size>100_000_000:raise ValueError("Export failed or size exceeded")
        report.update(pass_=True,objects=rows,triangles=sum(r["evaluated_triangles"] for r in rows),glb_sha256=sha(dest),glb_bytes=dest.stat().st_size)
        report["pass"]=report.pop("pass_")
    finally:save()
    print("GEOMETRY_NODES_BAKE",json.dumps(report))
def main():
    p=argparse.ArgumentParser();sp=p.add_subparsers(dest="mode",required=True)
    q=sp.add_parser("fixture");q.add_argument("blend",type=Path)
    q=sp.add_parser("bake");q.add_argument("blend",type=Path);q.add_argument("output",type=Path);q.add_argument("--sha256",required=True);q.add_argument("--collection")
    args=p.parse_args()
    if args.mode=="fixture":fixture(args.blend)
    else:bake(args.blend,args.output,args.sha256,args.collection)
if __name__=="__main__":main()
