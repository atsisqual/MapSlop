"""Import authorized OBJ/PLY/GLB into Blender, retain textures and consolidate objects by material.
Use with Blender 4.x Python. Input tree is verified before any import.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument("--input",type=Path,required=True);p.add_argument("--manifest",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    root=a.input.parent.resolve();m=json.loads(a.manifest.read_text())
    for k in ("source_type","license","author","reviewed_by","source_url_or_archive","files"):
        if not m.get(k):raise ValueError("Missing "+k)
    if m["source_type"] not in ("synthetic","DGT_LiDAR","DGT_orthophoto","owner_authorized_photos","authorized_open_asset"):raise ValueError("Unapproved source")
    if any(x in json.dumps(m).lower() for x in ("google earth","google maps","street view","portoslop")):raise ValueError("Excluded source")
    # Strict bundle: every file, including textures and material references, must be inventoried.
    for name,digest in m["files"].items():
        f=(root/name).resolve()
        if not f.is_relative_to(root) or not f.is_file() or sha(f)!=digest:raise ValueError("Invalid file "+name)
    if a.input.name not in m["files"]:raise ValueError("Input not inventoried")
    if a.input.suffix.lower()==".obj":
        for line in a.input.read_text(errors="strict").splitlines():
            if line.startswith("mtllib "):
                name=line[7:].strip()
                if name not in m["files"] or Path(name).name!=name:raise ValueError("Unverified MTL")
                for l in (root/name).read_text().splitlines():
                    if l.lower().startswith(("map_","bump ","disp ","norm ")):
                        ref=l.split()[-1]
                        if ref not in m["files"] or Path(ref).name!=ref:raise ValueError("Unverified texture")
    if a.input.suffix.lower()==".glb":
        import struct
        data=a.input.read_bytes();n=struct.unpack_from("<I",data,12)[0];j=json.loads(data[20:20+n])
        if any("uri" in v for v in j.get("buffers",[])+j.get("images",[])):raise ValueError("Self-contained GLB required")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if a.input.suffix.lower()==".obj":bpy.ops.wm.obj_import(filepath=str(a.input),forward_axis="NEGATIVE_Z",up_axis="Y")
    elif a.input.suffix.lower()==".ply":bpy.ops.wm.ply_import(filepath=str(a.input))
    elif a.input.suffix.lower()==".glb":bpy.ops.import_scene.gltf(filepath=str(a.input))
    else:raise ValueError("Only OBJ/PLY/GLB supported")
    def stats():
        objs=[o for o in bpy.context.scene.objects if o.type=="MESH"]
        if not objs:raise ValueError("No meshes")
        for o in objs:o.data.calc_loop_triangles()
        coords=[o.matrix_world@Vector(v) for o in objs for v in o.bound_box]
        return {"objects":len(objs),"triangles":sum(len(o.data.loop_triangles) for o in objs),"bounds":[[min(p[i] for p in coords) for i in range(3)],[max(p[i] for p in coords) for i in range(3)]],"textures":sorted(i.name for i in bpy.data.images if i.size[0]>0)}
    bpy.context.view_layer.update();before=stats()
    groups={}
    for o in bpy.context.scene.objects:
        if o.type=="MESH" and len(o.data.materials)==1 and o.data.materials[0]:
            groups.setdefault(o.data.materials[0].name,[]).append(o)
    for group in groups.values():
        if len(group)<2:continue
        bpy.ops.object.select_all(action="DESELECT")
        for o in group:o.select_set(True)
        bpy.context.view_layer.objects.active=group[0];bpy.ops.object.join()
    bpy.context.view_layer.update();after=stats()
    a.output.mkdir(parents=True,exist_ok=False);out=a.output/"converted.glb"
    bpy.ops.export_scene.gltf(filepath=str(out),export_format="GLB",export_yup=True)
    drift=max(abs(x-y) for aa,bb in zip(before["bounds"],after["bounds"]) for x,y in zip(aa,bb))
    r={"pass":before["triangles"]==after["triangles"] and drift<=.001 and out.stat().st_size>0,"source":before,"converted":after,"bbox_drift_m":drift,"output_sha256":sha(out),"blender":bpy.app.version_string,"source_manifest":m}
    (a.output/"import-report.json").write_text(json.dumps(r,indent=2)+"\n");print("ASSET_IMPORT",json.dumps(r))
    if not r["pass"]:raise RuntimeError("Import changed source geometry")
if __name__=="__main__":main()
