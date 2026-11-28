"""Test geospatial adapter on known coordinates, including nonzero SUMO offset."""
import importlib.util,sys,tempfile,unittest,xml.etree.ElementTree as ET,json,struct
from pathlib import Path
import numpy as np
from pyproj import Transformer
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"tools"))
spec=importlib.util.spec_from_file_location("infraframe",ROOT/"tools/infrastructure-frame.py");m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from terrain_grid import to_world,ORIGIN
class TestFrame(unittest.TestCase):
    def test_sumo_offset_controls(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);osm=ET.Element("osm");net=ET.Element("net");crs="EPSG:32629";offset=(-550000.,-4580000.)
            ET.SubElement(net,"location",netOffset=",".join(map(str,offset)),projParameter=crs)
            t=Transformer.from_crs(4326,32629,always_xy=True);coords=[]
            for i,(lon,lat) in enumerate([(ORIGIN[1],ORIGIN[0]),(ORIGIN[1]+.001,ORIGIN[0]),(ORIGIN[1],ORIGIN[0]+.001)],1):
                ET.SubElement(osm,"node",id=str(i),lon=str(lon),lat=str(lat));x,y=t.transform(lon,lat);x+=offset[0];y+=offset[1];coords.append((x,y))
                ET.SubElement(net,"junction",id=str(i),x=str(x),y=str(y),type="priority")
            e=ET.SubElement(net,"edge",id="10",**{"from":"1","to":"2"});ET.SubElement(e,"lane",id="10_0",index="0",width="3.2",shape=" ".join(f"{x},{y}" for x,y in coords[:2]))
            ET.ElementTree(osm).write(d/"map.osm");ET.ElementTree(net).write(d/"net.xml")
            lanes,r=m.sumo(d/"net.xml",d/"map.osm")
            self.assertTrue(r["pass"]);self.assertLess(r["control_max_m"],1e-5);self.assertTrue(np.allclose(lanes[0]["xz"][1],to_world(ORIGIN[1]+.001,ORIGIN[0]),atol=1e-5))
            net.find("junction[@id='2']").set("x",str(coords[1][0]+5));ET.ElementTree(net).write(d/"net.xml")
            _,r=m.sumo(d/"net.xml",d/"map.osm");self.assertFalse(r["pass"])
    def test_lifted_semantic_glb(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);t=Transformer.from_crs(4326,3763,always_xy=True);x,y=t.transform(ORIGIN[1],ORIGIN[0])
            src=d/"lift.obj";src.write_text(f"v {x} {y} 100\nv {x+5} {y} 100\nv {x} {y+3} 100\nv {x} {y} 101.5\nv {x+5} {y} 101.5\nv {x} {y+3} 101.5\nusemtl Road\nf 1 2 3\nusemtl Separation\nf 4 5 6\n")
            r=m.obj_to_glb(src,d/"scene.glb","EPSG:3763",100)
            self.assertEqual(r["triangles"],2);self.assertEqual(r["semantic_materials"]["Separation"]["height_range_m"],[1.5,1.5]);self.assertLess(abs(r["bounds"][0][0]),.001)
            raw=(d/"scene.glb").read_bytes();n=struct.unpack_from("<I",raw,12)[0];j=json.loads(raw[20:20+n]);self.assertEqual([a["name"] for a in j["materials"]],["Road","Separation"])
            self.assertAlmostEqual(r["bounds"][1][1],1.5)
if __name__=="__main__":unittest.main()
