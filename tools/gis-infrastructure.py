#!/usr/bin/env python3
"""Offline GDAL vector conversion, explicit CRS, geometry and attribute preservation.
DXF may lack CRS and stable GIS IDs; refuse implicit georeferencing.
"""
import argparse,hashlib,json,math
from pathlib import Path
from osgeo import gdal,ogr,osr
gdal.UseExceptions()
def hashfile(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inspect(path):
    ds=gdal.OpenEx(str(path),gdal.OF_VECTOR)
    if ds is None:raise ValueError("Cannot open vector source")
    rows=[]
    for layer in ds:
        crs=layer.GetSpatialRef()
        fields=[f.GetName() for f in layer.schema]
        n=0;geom=[];attrs=[]
        for f in layer:
            g=f.GetGeometryRef()
            if not g or g.IsEmpty():raise ValueError("Empty geometry")
            geom.append(g.ExportToIsoWkt());attrs.append({k:f.GetField(k) for k in fields});n+=1
        rows.append({"layer":layer.GetName(),"count":n,"crs_wkt":crs.ExportToWkt() if crs else None,"fields":fields,"extent":list(layer.GetExtent()),"geometry":geom,"attributes":attrs})
    if not rows or not sum(r["count"] for r in rows):raise ValueError("No features")
    return rows
def convert(source,dest,source_epsg=None,target_epsg=3763):
    original=inspect(source)
    if not source_epsg and any(not r["crs_wkt"] for r in original):raise ValueError("Missing source CRS, supply measured EPSG")
    if source_epsg:
        ref=osr.SpatialReference();ref.ImportFromEPSG(source_epsg)
        for r in original:
            if r["crs_wkt"]:
                actual=osr.SpatialReference();actual.ImportFromWkt(r["crs_wkt"])
                if not actual.IsSame(ref):raise ValueError("Explicit source CRS contradicts embedded CRS")
    opts=gdal.VectorTranslateOptions(format="GPKG",srcSRS=f"EPSG:{source_epsg}" if source_epsg else None,dstSRS=f"EPSG:{target_epsg}")
    output=gdal.VectorTranslate(str(dest),str(source),options=opts)
    if output is None:raise ValueError("GDAL translation failed")
    output=None;converted=inspect(dest)
    if len(original)!=len(converted):raise ValueError("Layer count changed")
    for x,y in zip(original,converted):
        if x["count"]!=y["count"]:raise ValueError("Feature count changed")
        if any(k not in y["fields"] for k in x["fields"]):raise ValueError("Source attributes lost")
        if x["attributes"]!=[{k:a[k] for k in x["fields"]} for a in y["attributes"]]:raise ValueError("Attributes changed")
        ref=osr.SpatialReference();ref.ImportFromWkt(y["crs_wkt"]);expected=osr.SpatialReference();expected.ImportFromEPSG(target_epsg)
        if not ref.IsSame(expected):raise ValueError("Output CRS mismatch")
    return {"pass":True,"gdal":gdal.VersionInfo("--version"),"source":str(source),"source_sha256":hashfile(source),"target":str(dest),"target_sha256":hashfile(dest),"target_epsg":target_epsg,"source_layers":original,"target_layers":converted}
def fixture(root):
    root.mkdir(parents=True,exist_ok=False);shp=root/"road.shp";dxf=root/"road.dxf"
    ref=osr.SpatialReference();ref.ImportFromEPSG(3763)
    driver=ogr.GetDriverByName("ESRI Shapefile");ds=driver.CreateDataSource(str(shp));layer=ds.CreateLayer("road",ref,ogr.wkbLineString25D);layer.CreateField(ogr.FieldDefn("asset_id",ogr.OFTString))
    f=ogr.Feature(layer.GetLayerDefn());f.SetField("asset_id","qa-road");g=ogr.CreateGeometryFromWkt("LINESTRING Z (-50000 180000 100,-49995 180003 101)");f.SetGeometry(g);assert layer.CreateFeature(f)==0;f=None;ds=None
    # Same original XYZ line in CAD, without embedded CRS.
    ds=ogr.GetDriverByName("DXF").CreateDataSource(str(dxf));layer=ds.CreateLayer("entities",geom_type=ogr.wkbLineString25D);f=ogr.Feature(layer.GetLayerDefn());f.SetGeometry(g);assert layer.CreateFeature(f)==0;f=None;ds=None
    a=convert(shp,root/"road-shp.gpkg");b=convert(dxf,root/"road-dxf.gpkg",3763)
    for r in (a,b):
        coords=ogr.CreateGeometryFromWkt(r["target_layers"][0]["geometry"][0]).GetPoints()
        assert len(coords)==2 and all(abs(x-y)<1e-5 for p,q in zip(coords,[(-50000,180000,100),(-49995,180003,101)]) for x,y in zip(p,q)),coords
    try:convert(dxf,root/"bad.gpkg")
    except ValueError:pass
    else:raise AssertionError("DXF without CRS accepted")
    # Actual reprojection and inverse transform, retaining Z and attributes.
    w=convert(shp,root/"road-wgs84.gpkg",target_epsg=4326);back=convert(root/"road-wgs84.gpkg",root/"road-back.gpkg")
    coords=ogr.CreateGeometryFromWkt(back["target_layers"][0]["geometry"][0]).GetPoints()
    err=max(math.dist(p,q) for p,q in zip(coords,[(-50000,180000,100),(-49995,180003,101)]));assert err<.01,err
    return {"pass":True,"gdal":gdal.VersionInfo("--version"),"shp":a,"dxf":b,"roundtrip_error_m":err,"missing_crs_rejected":True,"z_preserved":True}
def main():
    p=argparse.ArgumentParser();p.add_argument("--fixture",type=Path);p.add_argument("--input",type=Path);p.add_argument("--output",type=Path);p.add_argument("--source-epsg",type=int);p.add_argument("--target-epsg",type=int,default=3763);a=p.parse_args()
    if a.fixture:r=fixture(a.fixture);out=a.fixture
    else:
        if not a.input or not a.output:raise ValueError("Input and output required")
        a.output.mkdir(parents=True,exist_ok=False);out=a.output;r=convert(a.input,out/"converted.gpkg",a.source_epsg,a.target_epsg)
    (out/"report.json").write_text(json.dumps(r,indent=2,default=str)+"\n");print("GIS_CONVERSION",json.dumps({k:v for k,v in r.items() if k not in ("source_layers","target_layers","shp","dxf")}))
if __name__=="__main__":main()
