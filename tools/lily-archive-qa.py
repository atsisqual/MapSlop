#!/usr/bin/env python3
"""Verify exact owner-supplied Lily archives and exercise original local PBR mapping.
No network, no bundled native libraries, no Blender mock beyond preference injection.
"""
import argparse,ast,hashlib,json,socket,sys,tempfile,types,zipfile
from pathlib import Path,PurePosixPath
from PIL import Image
EXPECTED={
'LilyTexturePacker-v1.1.3-64bit.zip':('LilyTexturePacker','5ab76e7ff1b7294aea71e77d791e06cf138509ce536448fbeaf4987a58496554'),
'LilySurfaceScraper-v1.9.0.zip':('LilySurfaceScraper','f3972a400a64c19314fbfe29b8de7b7073306c8e49423d3119262b7a701165ba')}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inspect(path,root):
    package,expected=EXPECTED[path.name]
    actual=digest(path)
    if actual!=expected:raise ValueError('Archive hash mismatch')
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:raise ValueError('CRC failure')
        names=z.namelist();seen=set();count=0
        for i in z.infolist():
            p=PurePosixPath(i.filename)
            if p.is_absolute() or '..' in p.parts or '\\' in i.filename or p.parts[0]!=package or i.filename in seen or (i.external_attr>>16)&0o170000==0o120000:raise ValueError('Unsafe ZIP entry')
            seen.add(i.filename)
            if i.filename.endswith('.py') and 'site-packages' not in p.parts:
                data=z.read(i);ast.parse(data.decode('utf-8-sig'));count+=1
                if package=='LilySurfaceScraper':
                    dest=root.joinpath(*p.parts);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        return {'sha256':actual,'bytes':path.stat().st_size,'entries':len(names),'python_modules_parsed':count,'crc_pass':True,'native_modules':[n for n in names if n.endswith(('.so','.pyd','.dll','.dylib'))]}
def scraper_test(root):
    pkg=types.ModuleType('LilySurfaceScraper');pkg.__path__=[str(root/'LilySurfaceScraper')];sys.modules[pkg.__name__]=pkg
    pref=types.ModuleType(pkg.__name__+'.preferences');pref.getPreferences=lambda:types.SimpleNamespace(texture_dir=str(root/'cache'));sys.modules[pref.__name__]=pref
    def denied(*args,**kwargs):raise RuntimeError('Network forbidden')
    socket.socket.connect=denied;socket.socket.connect_ex=denied;socket.create_connection=denied
    from LilySurfaceScraper.MaterialData import MaterialData
    from LilySurfaceScraper.ScrapersManager import ScrapersManager
    from LilySurfaceScraper.Scrapers.LocalDirectoryScraper import LocalDirectoryScraper
    from LilySurfaceScraper.metadataHandler import Metadata
    ScrapersManager.all_scrapers=[LocalDirectoryScraper]
    folder=root/'inputs'/'granite';folder.mkdir(parents=True)
    expected={}
    for label,color in [('baseColor',(123,121,112)),('normal',(128,128,255)),('roughness',(210,210,210)),('metallic',(0,0,0)),('ambientOcclusion',(245,245,245)),('height',(90,90,90))]:
        p=folder/('granite_'+label+'.png');Image.new('RGB',(16,16),color).save(p);expected[label]=str(p)
    m=MaterialData(str(folder),texture_root=str(root));assert m.error is None
    assert m.getVariantList()==[str(folder)] and m.selectVariant(0)
    assert {k:v for k,v in m.maps.items() if v is not None}==expected
    assert all(Path(p).is_file() for p in expected.values())
    deep=MaterialData(str(folder.parent),texture_root=str(root),asset_name='LOCAL_FILE_SCRAPER-SUBDIR');assert deep.getVariantList()==['granite'] and deep.selectVariant(0)
    assert {k:v for k,v in deep.maps.items() if v is not None}==expected
    meta=root/'metadata.json';m.metadata.save(str(meta));reloaded=Metadata.open(str(meta));assert reloaded.variants==m.metadata.variants
    bad=MaterialData(str(root/'missing'),texture_root=str(root));assert bad.error is not None and bad.getVariantList() is None
    return {'pass':True,'scope':'original MaterialData + LocalDirectoryScraper + Metadata, preference shim only; no bpy or provider API','maps':sorted(expected),'variants':1,'deep_directory_pass':True,'metadata_roundtrip_pass':True,'missing_path_rejected':True,'fixture_sha256':{k:digest(Path(v)) for k,v in expected.items()}}
def main():
    p=argparse.ArgumentParser();p.add_argument('archives',type=Path);p.add_argument('report',type=Path);a=p.parse_args();r={'archives':{}}
    with tempfile.TemporaryDirectory(prefix='mapslop-lily-') as tmp:
        root=Path(tmp)
        for name in EXPECTED:r['archives'][name]=inspect(a.archives/name,root)
        r['surface_scraper_local']=scraper_test(root)
    r['texture_packer_runtime']={'pass':False,'status':'not_run_in_this_python_test','required':'Blender 2.83 x64 / CPython 3.7'}
    r['full_blender_material_graph']={'status':'not_run_in_this_python_test','required':'Blender >=4.1 with compatible lxml'}
    a.report.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
