"""Run original Lily add-on end-to-end in matching Blender on synthetic inputs.
Execute only in a disposable offline environment; no native add-on is committed.
Usage: blender -b --factory-startup --python-exit-code 1 --python tools/lily-blender-qa.py -- ZIP REPORT
"""
import sys,json,hashlib,zipfile,tempfile,socket
from pathlib import Path
import bpy,addon_utils,numpy as np
EXPECTED={
"LilyTexturePacker-v1.1.3-64bit.zip":("LilyTexturePacker","5ab76e7ff1b7294aea71e77d791e06cf138509ce536448fbeaf4987a58496554",(3,7)),
"LilySurfaceScraper-v1.9.0.zip":("LilySurfaceScraper","f3972a400a64c19314fbfe29b8de7b7073306c8e49423d3119262b7a701165ba",(3,11))}
archive,report_path=map(Path,sys.argv[sys.argv.index("--")+1:])
package,expected,abi=EXPECTED[archive.name]
report={"pass":False,"archive":archive.name,"sha256":expected,"blender":bpy.app.version_string,"python":sys.version}
def denied(*a,**k):raise RuntimeError("Network forbidden")
def packer():
    from LilyTexturePacker.packing import pack_textures,get_image_node
    from LilyTexturePacker.LilyPack import pack
    placements,w,h=pack(np.array([[13,17],[9,11]],dtype=np.int32))
    assert len(placements)==2 and w>=9 and h>=9
    objects=[];colors=[(.75,.1,.15,1.),(.1,.7,.2,1.)]
    for i,(size,color) in enumerate(zip([(16,20),(12,18)],colors)):
        mesh=bpy.data.meshes.new("QA mesh "+str(i));mesh.from_pydata([(0,0,0),(1,0,0),(0,1,0)],[],[(0,1,2)]);mesh.update()
        o=bpy.data.objects.new("QA "+str(i),mesh);bpy.context.collection.objects.link(o);o.location.x=2*i
        uv=mesh.uv_layers.new(name="UVMap")
        for d,v in zip(uv.data,[(.2,.2),(.8,.2),(.2,.8)]):d.uv=v
        img=bpy.data.images.new("QA image "+str(i),width=size[0],height=size[1],alpha=True,float_buffer=True)
        img.pixels.foreach_set(np.tile(np.array(color,np.float32),size[0]*size[1]))
        mat=bpy.data.materials.new("QA material "+str(i));mat.use_nodes=True
        node=mat.node_tree.nodes.new("ShaderNodeTexImage");node.image=img
        mat.node_tree.links.new(node.outputs["Color"],mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
        o.data.materials.append(mat);objects.append(o)
    pack_textures(objects,spacing=0)
    images=[get_image_node(o).image for o in objects];assert images[0]==images[1]
    image=images[0];w,h=image.size
    rgba=np.zeros(w*h*4,np.float32);image.pixels.foreach_get(rgba);rgba=rgba.reshape(h,w,4)
    errors=[]
    for o,color in zip(objects,colors):
        assert len(o.data.vertices)==3 and len(o.data.polygons)==1
        uvs=np.array([list(d.uv) for d in o.data.uv_layers.active.data])
        assert (uvs>=0).all() and (uvs<=1).all()
        u,v=uvs.mean(axis=0);sample=rgba[min(h-1,int(v*h)),min(w-1,int(u*w))]
        errors.append(float(np.max(np.abs(sample-np.array(color)))))
    assert max(errors)<=.03,errors
    return {"native_pack_pass":True,"objects":2,"atlas_size":[w,h],"max_color_error":max(errors),"triangles_preserved":True,"scope":"two single-material base-color synthetic meshes; not multi-PBR maps"}
def scraper(root):
    from LilySurfaceScraper.CyclesMaterialData import CyclesMaterialData
    from LilySurfaceScraper.ScrapersManager import ScrapersManager
    from LilySurfaceScraper.Scrapers.LocalDirectoryScraper import LocalDirectoryScraper
    ScrapersManager.all_scrapers=[LocalDirectoryScraper]
    folder=root/"granite";folder.mkdir()
    for key,color in [("baseColor",(.4,.4,.4,1)),("normal",(.5,.5,1,1)),("roughness",(.8,.8,.8,1)),("metallic",(0,0,0,1)),("height",(.5,.5,.5,1)),("ambientOcclusion",(1,1,1,1))]:
        img=bpy.data.images.new("fixture "+key,width=16,height=16)
        img.pixels.foreach_set(np.tile(np.array(color,np.float32),16*16));img.filepath_raw=str(folder/(key+".png"));img.file_format="PNG";img.save()
    m=CyclesMaterialData(str(folder),texture_root=str(root));assert m.getVariantList()==[str(folder)] and m.selectVariant(0)
    mat=m.createMaterial();p=next(n for n in mat.node_tree.nodes if n.type=="BSDF_PRINCIPLED")
    for name in ("Base Color","Roughness","Metallic","Normal"):assert p.inputs[name].is_linked,name
    return {"local_material_graph_pass":True,"maps":[k for k,v in m.maps.items() if v is not None],"nodes":len(mat.node_tree.nodes),"scope":"real Blender graph from own local maps; no provider API"}
try:
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected
    assert sys.version_info[:2]==abi,("Incorrect Python ABI",sys.version,abi)
    if package=="LilySurfaceScraper":assert bpy.app.version>=(4,1,0)
    with tempfile.TemporaryDirectory(prefix="mapslop-lily-blender-") as d:
        root=Path(d)
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            for i in z.infolist():
                path=Path(i.filename)
                assert not path.is_absolute() and ".." not in path.parts and path.parts[0]==package and "\\" not in i.filename and (i.external_attr>>16)&0o170000!=0o120000
            z.extractall(root)
        socket.socket.connect=denied;socket.socket.connect_ex=denied;socket.create_connection=denied
        sys.path.insert(0,str(root))
        addon_utils.enable(package,default_set=False,persistent=False)
        assert addon_utils.check(package)[1],"Registration failed"
        report.update(packer() if package=="LilyTexturePacker" else scraper(root))
        report["pass"]=True
finally:
    report_path.write_text(json.dumps(report,indent=2)+"\n")
print("LILY_BLENDER_QA",json.dumps(report))
