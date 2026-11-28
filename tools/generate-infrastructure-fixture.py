#!/usr/bin/env python3
"""Synthetic IFC wall, 5 m x .2 m x 3 m, plus CityJSON wall solid."""
import sys,json
from pathlib import Path
import numpy as np
import ifcopenshell.api
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
run=ifcopenshell.api.run
m=run("project.create_file",version="IFC4")
project=run("root.create_entity",m,ifc_class="IfcProject",name="MapSlop synthetic fixture")
run("unit.assign_unit",m)
context=run("context.add_context",m,context_type="Model")
body=run("context.add_context",m,context_type="Model",context_identifier="Body",target_view="MODEL_VIEW",parent=context)
wall=run("root.create_entity",m,ifc_class="IfcWall",name="QA wall")
rep=run("geometry.add_wall_representation",m,context=body,length=5.,height=3.,thickness=.2)
run("geometry.assign_representation",m,product=wall,representation=rep)
run("geometry.edit_object_placement",m,product=wall,matrix=np.eye(4),is_si=True)
m.write(str(out/"wall.ifc"))
v=[[0,0,0],[500,0,0],[500,20,0],[0,20,0],[0,0,300],[500,0,300],[500,20,300],[0,20,300]]
surfaces=[[[3,2,1,0]],[[0,1,5,4]],[[1,2,6,5]],[[2,3,7,6]],[[3,0,4,7]],[[4,5,6,7]]]
doc={"type":"CityJSON","version":"2.0","transform":{"scale":[.01,.01,.01],"translate":[0,0,0]},"CityObjects":{"qa-wall":{"type":"GenericCityObject","geometry":[{"type":"Solid","lod":"2","boundaries":[surfaces]}]}},"vertices":v}
(out/"wall.city.json").write_text(json.dumps(doc,indent=2))
