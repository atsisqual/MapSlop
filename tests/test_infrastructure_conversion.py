"""Offline infrastructure converter tests; preserve source node identities, topology and tags."""
import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("osmconv",ROOT/"tools/osm-json-to-xml.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_shared_nodes_and_excluded_relations(self):
        a={"lat":41.4,"lon":-8.4};b={"lat":41.4001,"lon":-8.4};c={"lat":41.4001,"lon":-8.399}
        doc={"elements":[{"type":"node","id":2,**b,"tags":{"highway":"crossing"}},{"type":"way","id":10,"nodes":[1,2],"geometry":[a,b],"tags":{"highway":"residential"}},{"type":"way","id":11,"nodes":[2,3],"geometry":[b,c],"tags":{"barrier":"wall"}},{"type":"relation","id":20,"members":[{"type":"way","ref":10,"role":"outer"},{"type":"way","ref":999,"role":"inner"}],"tags":{"type":"multipolygon"}}]}
        root,r=m.convert(doc);self.assertEqual(r["nodes"],3);self.assertEqual(r["ways"],2);self.assertEqual(r["relations"],0);self.assertEqual(r["excluded_relations"][0]["id"],20)
        self.assertEqual(root.find("node[@id='2']/tag[@k='highway']").get("v"),"crossing")
        self.assertEqual(root.find("way[@id='11']/nd").get("ref"),"2")
        _,r=m.convert(doc,[-8.401,41.399,-8.3999,41.401]);self.assertEqual(r["ways"],1);self.assertEqual(r["ways_excluded_not_wholly_inside"],1)
        _,r=m.convert(doc,mode="roads");self.assertEqual(r["ways"],1)
        doc["elements"][2]["geometry"][0]={"lat":41.5,"lon":-8.4}
        with self.assertRaises(ValueError):m.convert(doc)
    def test_actual_pedome_references(self):
        d=json.loads((ROOT/"data/pedome/pedome-osm.json").read_text());root,r=m.convert(d,[-8.395,41.4105,-8.383,41.4195])
        self.assertTrue(r["pass"]);self.assertGreater(r["ways"],50)
        nodes={n.get("id") for n in root.findall("node")};ways={w.get("id") for w in root.findall("way")}
        for w in root.findall("way"):
            self.assertTrue(all(n.get("ref") in nodes for n in w.findall("nd")))
        for e in root.findall("relation"):
            for n in e.findall("member"):self.assertIn(n.get("ref"),nodes if n.get("type")=="node" else ways)
        self.assertGreater(r["inventory"].get("barrier=wall",0),0)
if __name__=="__main__":unittest.main()
