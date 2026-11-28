"""Register actual pinned offline add-ons, test local GIS scene math.
No map capture imports, provider endpoints or third-party sample data.
"""
import sys,json,math,os
from pathlib import Path
import bpy,addon_utils
gis,mmi,out=map(Path,sys.argv[sys.argv.index("--")+1:])
report={"pass":False,"blender":bpy.app.version_string,"addons":{}}
def save():out.write_text(json.dumps(report,indent=2)+"\n")
try:
    # Prevent automatic remote CRS fallback or network access from the add-ons.
    import socket
    def denied(*a,**k):raise RuntimeError("Network forbidden in addon QA")
    socket.socket.connect=denied;socket.socket.connect_ex=denied;socket.create_connection=denied
    os.environ["PYTHONHTTPSVERIFY"]="1"
    for path in (gis,mmi):
        sys.path.insert(0,str(path.parent))
        addon_utils.enable(path.name,default_set=False,persistent=False)
        module=sys.modules.get(path.name)
        if not module or not addon_utils.check(path.name)[1]:raise RuntimeError("Addon failed to enable: "+path.name)
        report["addons"][path.name]={"registered":True,"version":list(module.bl_info["version"])}
    from BlenderGIS.geoscene import GeoScene
    from BlenderGIS.core.settings import settings
    from BlenderGIS.core.proj.reproj import reprojPt
    settings.proj_engine="BUILTIN"
    g=GeoScene();g.crs="EPSG:3857";g.scale=1.;g.setOriginGeo(-8.4,41.4)
    if not g.isFullyGeoref:raise ValueError("Scene failed georef")
    origin=g.getOriginPrj();p=g.view3dToProj(12.5,-8.25);q=g.projToView3d(*p)
    lon,lat=reprojPt(3857,4326,*origin)
    err=max(abs(q[0]-12.5),abs(q[1]+8.25))
    assert err<1e-6 and max(abs(lon+8.4),abs(lat-41.4))<1e-8
    report["addons"]["BlenderGIS"].update(crs=g.crs,origin_projected=origin,local_roundtrip_error_m=err,geographic_roundtrip_error_deg=max(abs(lon+8.4),abs(lat-41.4)))
    op=bpy.ops.import_rdc.google_maps.get_rna_type()
    assert op.identifier
    from MapsModelsImporter.google_maps import addMesh,addImageMaterial
    obj=addMesh(bpy.context,"MapSlop own triangle",[(0,0,0),(2,0,0),(0,1,0)],[(0,1,2)],[(0,0),(1,0),(0,1)])
    img=bpy.data.images.new("Own checker",width=2,height=2)
    img.pixels[:]=[1,0,0,1,0,1,0,1,0,0,1,1,1,1,1,1]
    addImageMaterial("Own material",obj,img)
    assert len(obj.data.vertices)==3 and len(obj.data.polygons)==1
    uv={tuple(round(v,5) for v in d.uv) for d in obj.data.uv_layers.active.data}
    assert uv=={(0.,0.),(1.,0.),(0.,1.)}
    assert any(n.type=="TEX_IMAGE" and n.image==img for m in obj.data.materials for n in m.node_tree.nodes)
    report["addons"]["MapsModelsImporter"].update(operator=op.identifier,synthetic_mesh_vertices=3,synthetic_mesh_faces=1,uv_verified=True,material_verified=True,scope="registration and upstream mesh/material helpers; RDC import not tested")
    report["pass"]=True
finally:save()
print("BLENDER_ADDON_QA",json.dumps(report))
