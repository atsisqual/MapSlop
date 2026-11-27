import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from road_profiles import solve,metrics,network
from road_carve import Corridor

class ProfileTests(unittest.TestCase):
    def test_shared_node_and_grade_constraint(self):
        ways=[{"way":1,"name":"a","ids":[0,1,2],"s":[0,3,6]},
              {"way":2,"name":"b","ids":[3,1,4],"s":[0,3,6]}]
        ref=np.array([0.,0.4,0.,0.1,-0.1])
        y=solve(ref,ways)
        for m in metrics(ref,y,ways):
            self.assertLessEqual(m["max_grade_change_per_3m"],0.020001)
            self.assertLessEqual(m["max_deviation_m"],0.5)
    def test_cross_section_and_berm(self):
        xy=np.array([[0.,0.],[3.,0.],[6.,0.]])
        y=np.array([0.,0.3,0.6])
        c=Corridor(xy,y,[{"ids":[0,1,2],"width_m":6}])
        p=np.array([[1.5,-2.],[1.5,0.],[1.5,2.],[1.5,4.25],[1.5,5.5],[1.5,7.]])
        out,w=c.target(p,np.ones(len(p)))
        np.testing.assert_allclose(out[:3],0.15)
        self.assertAlmostEqual(out[3],0.575)
        np.testing.assert_allclose(out[4:],1)
    def test_osm_shared_and_bridge_excluded(self):
        def way(i,n,coords,**tags):
            return {"type":"way","id":i,"nodes":n,"geometry":[{"lon":x,"lat":z} for x,z in coords],
                    "tags":{"highway":"residential",**tags}}
        a=(-8.3881,41.415);b=(-8.388,41.415);c=(-8.3879,41.415)
        d=(-8.388,41.4151)
        xy,ways,nodes,shared,excluded=network({"elements":[way(1,[10,11,12],[a,b,c]),
            way(2,[11,13],[b,d]),way(3,[11,14],[b,d],bridge="yes")]})
        self.assertEqual(shared,{11})
        self.assertIn(nodes[11],ways[0]["ids"])
        self.assertIn(nodes[11],ways[1]["ids"])
        self.assertEqual(excluded[0]["way"],3)
