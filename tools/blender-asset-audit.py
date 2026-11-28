"""Offline Blender GLB geometry audit and optional LOD candidate from authorised data.
Run with blender --background --factory-startup --python-exit-code 1 --python this.py -- ...
No map captures, no network calls, no automatic publication.
"""
import argparse, hashlib, json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def meshes():
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]

def stats():
    objects=meshes()
    if not objects:raise ValueError("No mesh objects")
    coords=[o.matrix_world @ Vector(c) for o in objects for c in o.bound_box]
    lo=[min(v[i] for v in coords) for i in range(3)]
    hi=[max(v[i] for v in coords) for i in range(3)]
    triangles=0
    for o in objects:
        o.data.calc_loop_triangles()
        triangles+=len(o.data.loop_triangles)
    mats={m.name for o in objects for m in o.data.materials if m}
    images=[{"name":i.name,"width":int(i.size[0]),"height":int(i.size[1])}
            for i in bpy.data.images if i.type=="IMAGE" and i.size[0]>0]
    if not all(math.isfinite(v) for v in lo+hi):raise ValueError("Nonfinite bounds")
    return {"objects":len(objects),"triangles":triangles,"vertices":sum(len(o.data.vertices) for o in objects),
            "materials":len(mats),"images":images,"bbox_blender_z_up_m":[lo,hi]}

def export_glb(path):
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes():o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path),export_format="GLB",use_selection=True,export_yup=True)
    if not path.is_file():raise RuntimeError("No GLB produced")

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def fixture():
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=32,radius=2,location=(3,4,5))
    bpy.context.object.name="Synthetic QA only"
    bpy.ops.mesh.primitive_cube_add(size=1,location=(-1,-2,0))

def main():
    p=argparse.ArgumentParser();p.add_argument("--input",type=Path);p.add_argument("--provenance",type=Path)
    p.add_argument("--fixture",action="store_true");p.add_argument("--output",type=Path,required=True)
    p.add_argument("--ratio",type=float,default=.5);p.add_argument("--max-bound-drift-m",type=float,default=.1)
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    if not 0<a.ratio<1 or not 0<a.max_bound_drift_m<=.25:p.error("Invalid LOD thresholds")
    if a.fixture:
        if a.input or a.provenance:p.error("Fixture is independent of real assets")
        provenance={"source_type":"synthetic","license":"MIT"}
    else:
        if not a.input or not a.provenance or a.input.suffix.lower()!=".glb":p.error("GLB and provenance JSON required")
        provenance=json.loads(a.provenance.read_text())
        if provenance.get("source_type") not in {"DGT_LiDAR","DGT_orthophoto","owner_authorized_photos","authorized_open_asset"}:
            raise ValueError("Source not approved")
        for k in ("source_url_or_archive","license","author","sha256","reviewed_by"):
            if not provenance.get(k):raise ValueError("Missing provenance "+k)
        if provenance["sha256"]!=sha(a.input):raise ValueError("Asset hash mismatch")
        if any(x in json.dumps(provenance).lower() for x in ("google maps","google earth","street view","maps.google","earth.google","portoslop")):
            raise ValueError("Excluded provenance")
    a.output.mkdir(parents=True,exist_ok=False)
    reset()
    if a.fixture:fixture()
    else:bpy.ops.import_scene.gltf(filepath=str(a.input))
    bpy.context.view_layer.update()
    before=stats()
    if a.fixture:export_glb(a.output/"fixture-source.glb")
    # Keep transforms, material slots and UVs. No global weld across texture seams.
    # Decimation is a candidate only; visual fidelity requires separate review.
    for o in meshes():
        if len(o.data.polygons)<100:continue
        bpy.context.view_layer.objects.active=o
        mod=o.modifiers.new("MapSlop LOD candidate","DECIMATE");mod.ratio=a.ratio
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.context.view_layer.update()
    out=a.output/"lod-candidate.glb";export_glb(out)
    reset();bpy.ops.import_scene.gltf(filepath=str(out));bpy.context.view_layer.update();after=stats()
    drift=max(abs(x-y) for a1,b1 in zip(before["bbox_blender_z_up_m"],after["bbox_blender_z_up_m"]) for x,y in zip(a1,b1))
    report={"schema":1,"fixture":a.fixture,"blender":bpy.app.version_string,"provenance":provenance,
            "source":before,"candidate":after,"bbox_drift_m":drift,"output_bytes":out.stat().st_size,
            "output_sha256":sha(out),"visual_review_required":True,
            "pass":after["triangles"]<before["triangles"] and drift<=a.max_bound_drift_m}
    (a.output/"asset-audit.json").write_text(json.dumps(report,indent=2)+"\n")
    print("BLENDER_ASSET_AUDIT",json.dumps(report))
    if not report["pass"]:raise RuntimeError("LOD candidate rejected")
if __name__=="__main__":main()
