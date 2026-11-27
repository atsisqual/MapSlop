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

    def test_cdt_forces_diagonal(self):
        from road_carve import constrained_mesh
        p=np.array([[0,0],[100,0],[100,100],[0,100]],dtype=np.int64)
        faces,proof=constrained_mesh(p,np.array([[1,3]]))
        edges={tuple(sorted((int(a),int(b)))) for f in faces for a,b in zip(f,np.roll(f,-1))}
        self.assertIn((1,3),edges)
        self.assertEqual(proof["missing_mandatory_edges"],0)
    def test_flat_junction_platform(self):
        xy=np.array([[0.,0.],[3.,0.],[6.,0.],[3.,3.]])
        y=np.array([0.,0.3,0.6,0.6])
        c=Corridor(xy,y,[{"ids":[0,1,2],"width_m":6},{"ids":[1,3],"width_m":6}],[1])
        out,_=c.target(np.array([[3.,0.],[3.,1.],[4.,0.],[2.,-1.]]),np.ones(4))
        np.testing.assert_allclose(out,0.3)

    def test_access_exclusion_and_legacy(self):
        def way(i,kind,**tags):
            return {"type":"way","id":i,"nodes":[i*2,i*2+1],"geometry":[{"lon":-8.388,"lat":41.415},{"lon":-8.3879,"lat":41.415}],
                    "tags":{"highway":kind,**tags}}
        osm={"elements":[way(1,"residential"),way(2,"service",service="driveway"),way(3,"track")]}
        _,ways,_,_,excluded=network(osm)
        self.assertEqual([w["way"] for w in ways],[1])
        self.assertEqual({e["way"] for e in excluded},{2,3})
        self.assertEqual([w["way"] for w in network(osm,legacy=True)[1]],[1,2])
    def test_adaptive_limits_are_local(self):
        from road_profiles import curvature_limits,CURVATURE,ADAPTIVE_MAX_CURVATURE
        way={"way":1,"name":"r","ids":[0,1,2,3,4],"s":[0,3,6,9,12]}
        ref=np.array([0.,0.3,0.6,1.2,1.8])
        limits=curvature_limits(ref,[way],True)
        self.assertEqual(limits[0][3],CURVATURE)
        self.assertGreater(limits[1][3],CURVATURE)
        self.assertLessEqual(limits[1][3],ADAPTIVE_MAX_CURVATURE)
        self.assertEqual(limits[2][3],CURVATURE)
    def test_strip_plane_and_snap(self):
        xy=np.array([[0.,0.],[3.,0.],[6.,0.]])
        y=np.array([0.,0.3,0.6])
        c=Corridor(xy,y,[{"way":1,"ids":[0,1,2],"width_m":6}])
        c.install_strips()
        out,_=c.target(np.array([[1.5,-3.004],[1.5,0],[1.5,3.004]]),np.ones(3))
        np.testing.assert_allclose(out,0.15,atol=1e-8)
