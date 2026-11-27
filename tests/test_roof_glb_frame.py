import importlib.util
import json
import struct
import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
spec=importlib.util.spec_from_file_location("roofer_conversion",Path(__file__).resolve().parents[1]/"tools/convert-roofer-preview.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class GLBTests(unittest.TestCase):
    def test_read_scene_transformed_positions(self):
        # cjio stores (east,north,up); its root rotation converts to Y-up.
        world=np.array([[10.,-17.,23.],[20.,49.,-5.],[5.,20.,-2.]])
        raw=(world[:,[0,2,1]]*np.array([1,-1,1])).astype('<f4').tobytes()
        doc={"nodes":[{"matrix":[1,0,0,0,0,0,-1,0,0,1,0,0,0,0,0,1],"children":[1]},{"mesh":0}],
             "scenes":[{"nodes":[0]}],"meshes":[{"primitives":[{"attributes":{"POSITION":0}}]}],
             "accessors":[{"bufferView":0,"componentType":5126,"type":"VEC3","count":3}],
             "bufferViews":[{"byteOffset":0,"byteLength":len(raw)}]}
        j=json.dumps(doc).encode();j+=b" "*((-len(j))%4)
        payload=b"glTF"+struct.pack("<II",2,12+8+len(j)+8+len(raw))+struct.pack("<II",len(j),0x4e4f534a)+j+struct.pack("<II",len(raw),0x004e4942)+raw
        lo,hi=m.glb_world_bounds(payload)
        np.testing.assert_allclose(lo,world.min(axis=0))
        np.testing.assert_allclose(hi,world.max(axis=0))
