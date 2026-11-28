"""Run only the pinned upstream pure-coordinate module, never find_overlaps/network."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
from octant_to_latlong import LatLonBox,octant_to_latlong
b=LatLonBox(20,10,30,40)
assert b.mid_point==(15,35)
assert b.get_child('0')==(15,10,30,35)
assert b.get_child('3')==(20,15,35,40)
assert b.get_child('0').overlaps_with(LatLonBox(13,11,31,34))
assert not b.get_child('0').overlaps_with(LatLonBox(19,17,36,39))
assert octant_to_latlong('')==(90,-90,-180,180)
try:b.get_child('x')
except ValueError:pass
else:raise AssertionError('invalid octant accepted')
print(json.dumps({'pass':True,'scope':'pure geographic math only','upstream':'cd5c4d66760d44d1388ee9634a8d3a35876b284c'}))
