#!/usr/bin/env python3
"""Count imagery metadata across pilot cells; do not fetch image bytes or log URLs with credentials."""
import json,os,urllib.request,urllib.parse,urllib.error,time
from pathlib import Path

def main():
    token=os.environ.get("MAPILLARY_TOKEN")
    if not token:raise SystemExit("Missing MAPILLARY_TOKEN repository secret")
    west,south,east,north=-8.395,41.4105,-8.383,41.4195
    seen=set();cells=[]
    for j in range(4):
        for i in range(4):
            bbox=[west+(east-west)*i/4,south+(north-south)*j/4,west+(east-west)*(i+1)/4,south+(north-south)*(j+1)/4]
            query=urllib.parse.urlencode({"bbox":",".join(map(str,bbox)),"fields":"id","limit":2000})
            req=urllib.request.Request("https://graph.mapillary.com/images?"+query,headers={"Authorization":"OAuth "+token})
            try:
                with urllib.request.urlopen(req,timeout=30) as f:r=json.load(f)
            except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ValueError):raise SystemExit("Mapillary API query failed; coverage unknown (no token or URL logged)") from None
            if not isinstance(r.get("data"),list):raise SystemExit("Unexpected API response; coverage unknown")
            ids={x["id"] for x in r["data"]};seen.update(ids)
            cells.append({"bbox":bbox,"images_returned":len(ids),"potentially_truncated":bool(r.get("paging",{}).get("next")) or len(ids)>=2000})
            time.sleep(.25)
    out={"bbox":[west,south,east,north],"unique_images_lower_bound":len(seen),"nonempty_cells":sum(c["images_returned"]>0 for c in cells),"cells":cells,"complete":not any(c["potentially_truncated"] for c in cells),"note":"Metadata only; image count is not verified facade visibility or road coverage."}
    Path("mapillary-coverage.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({k:v for k,v in out.items() if k!="cells"}))
if __name__=="__main__":main()
