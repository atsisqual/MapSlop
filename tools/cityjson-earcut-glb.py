#!/usr/bin/env python3
"""Use cjio's original earcut path; never invoke Shewchuk Triangle."""
import sys
from pathlib import Path
from cjio import cityjson
source,dest=map(Path,sys.argv[1:])
with source.open() as f:
    cm=cityjson.CityJSON(file=f)
cm.triangulate(sloppy=True)
result=cm.export2glb(do_triangulate=False)
if hasattr(result,"getvalue"):result=result.getvalue()
if not isinstance(result,(bytes,bytearray)):raise TypeError("Unexpected cjio GLB output")
dest.write_bytes(result)
