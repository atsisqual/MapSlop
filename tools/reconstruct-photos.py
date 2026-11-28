#!/usr/bin/env python3
"""Execute external offline reconstruction tools on a verified photo set.
Every actual stage checks its output, logs commands and retains failures.
Run in a dedicated environment; never a map service endpoint.
"""
import argparse,hashlib,importlib.util,json,os,shutil,subprocess,time
from pathlib import Path
spec=importlib.util.spec_from_file_location("assets",Path(__file__).with_name("asset-pipeline.py"))
assets=importlib.util.module_from_spec(spec);spec.loader.exec_module(assets)

def run_photos(root,manifest,out,backend,odm_image=None):
    root=root.resolve();out=out.resolve();m=assets.provenance(root,manifest)
    photos=sorted(root/n for n in m["files"] if Path(n).suffix.lower() in {".jpg",".jpeg",".png",".tif",".tiff"})
    if len(photos)<8:raise ValueError("At least eight inventoried photos required")
    out.mkdir(parents=True,exist_ok=False);images=out/"images";images.mkdir()
    if len({p.name for p in photos})!=len(photos):raise ValueError("Duplicate photo basenames")
    for p in photos:shutil.copy2(p,images/p.name)
    report={"backend":backend,"input_manifest":m,"stages":[],"pass":False}
    def save():(out/"reconstruction-report.json").write_text(json.dumps(report,indent=2)+"\n")
    def command(name,args,expected=()):
        exe=shutil.which(args[0]);r={"stage":name,"args":list(map(str,args)),"executable":exe,"status":"running"};report["stages"].append(r);save()
        if not exe:r["status"]="missing_dependency";save();raise RuntimeError("Missing "+args[0])
        r["executable_sha256"]=assets.sha(Path(exe));start=time.monotonic()
        try:
            with (out/(name+".log")).open("w") as log:
                result=subprocess.run(list(map(str,args)),cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=7200)
            r.update(exit_code=result.returncode,seconds=round(time.monotonic()-start,2),outputs={str(p):p.stat().st_size if p.is_file() else None for p in expected})
            r["status"]="pass" if result.returncode==0 and all(p.is_file() and p.stat().st_size>0 for p in expected) else "failed"
            if r["status"]!="pass":
                print((out/(name+".log")).read_text(errors="replace")[-16000:],flush=True)
                raise RuntimeError("Failed stage "+name)
        except Exception as e:r["error"]=str(e);r["status"]="failed";raise
        finally:save()
    try:
        if backend=="odm":
            if not odm_image or "@sha256:" not in odm_image:raise ValueError("ODM image must be digest pinned")
            # Copy verified imagery into a dedicated project. Docker has no network during reconstruction.
            project=out/"odm";project.mkdir();shutil.copytree(images,project/"images")
            if "geo.txt" in m["files"]:shutil.copy2(root/"geo.txt",project/"geo.txt")
            command("odm",["docker","run","--rm","--network","none","-v",f"{out}:/datasets",odm_image,"--project-path","/datasets","odm","--dsm","--orthophoto-resolution","5","--feature-quality","medium","--pc-quality","low","--max-concurrency","2"],[project/"odm_texturing/odm_textured_model_geo.obj",project/"odm_orthophoto/odm_orthophoto.tif"])
        else:
            db=out/"database.db";sparse=out/"sparse";sparse.mkdir()
            intrinsics=[]
            if m.get("camera_params"):
                intrinsics=["--ImageReader.camera_model","PINHOLE","--ImageReader.camera_params",",".join(map(str,m["camera_params"]))]
            command("features",["colmap","feature_extractor","--database_path",db,"--image_path",images,"--ImageReader.single_camera","1","--SiftExtraction.use_gpu","0","--SiftExtraction.num_threads","2",*intrinsics],[db])
            command("matches",["colmap","exhaustive_matcher","--database_path",db,"--SiftMatching.use_gpu","0","--SiftMatching.num_threads","2"],[db])
            command("mapper",["colmap","mapper","--database_path",db,"--image_path",images,"--output_path",sparse,"--Mapper.num_threads","2"])
            models=[p for p in sparse.iterdir() if p.is_dir() and (p/"points3D.bin").is_file()]
            if not models:raise RuntimeError("No sparse model")
            model=max(models,key=lambda p:(p/"points3D.bin").stat().st_size)
            # COLMAP binary headers contain uint64 counts.
            count=lambda p:int.from_bytes(p.read_bytes()[:8],"little")
            report["registered_images"]=count(model/"images.bin");report["sparse_points"]=count(model/"points3D.bin")
            if report["registered_images"]<max(4,len(photos)//2) or report["sparse_points"]<30:raise RuntimeError("Sparse reconstruction insufficient")
            if backend=="openmvs":
                dense=out/"dense"
                command("undistort",["colmap","image_undistorter","--image_path",images,"--input_path",model,"--output_path",dense,"--output_type","COLMAP"],[dense/"sparse/images.bin"])
                scene=out/"scene.mvs";cloud=out/"scene_dense.mvs";mesh=out/"scene_mesh.mvs";tex=out/"scene_textured.mvs"
                command("interface",["InterfaceCOLMAP","-i",dense,"-o",scene,"--image-folder",dense/"images"],[scene])
                command("densify",["DensifyPointCloud","-i",scene,"-o",cloud,"--resolution-level","1","--max-threads","2"],[cloud])
                command("mesh",["ReconstructMesh","-i",cloud,"-o",mesh,"--max-threads","2"],[mesh])
                command("texture",["TextureMesh","-i",mesh,"-o",tex,"--max-threads","2","--export-type","obj"],[out/"scene_textured.obj"])
        report["pass"]=True
    finally:save()
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument("backend",choices=["colmap","openmvs","odm"]);p.add_argument("--input",type=Path,required=True);p.add_argument("--manifest",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--odm-image");a=p.parse_args()
    print(json.dumps(run_photos(a.input,a.manifest,a.output,a.backend,a.odm_image),indent=2))
if __name__=="__main__":main()
