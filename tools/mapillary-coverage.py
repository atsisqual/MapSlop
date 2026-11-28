#!/usr/bin/env python3
"""Count imagery metadata across pilot cells; do not fetch image bytes or log URLs with credentials."""
import json,os,urllib.request,urllib.parse,urllib.error,time
from pathlib import Path

def scan(token,bounds,n=4):
    west,south,east,north=bounds
    seen=set();cells=[]
    for j in range(n):
        for i in range(n):
            bbox=[west+(east-west)*i/n,south+(north-south)*j/n,west+(east-west)*(i+1)/n,south+(north-south)*(j+1)/n]
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
    return out

def main():
    token=os.environ.get("MAPILLARY_TOKEN")
    if not token:raise SystemExit("Missing MAPILLARY_TOKEN repository secret")
    pilot=scan(token,[-8.395,41.4105,-8.383,41.4195])
    controls={"famalicao_centro":scan(token,[-8.522,41.404,-8.515,41.410],2)}
    if not controls["famalicao_centro"]["unique_images_lower_bound"]:
        controls["lisboa_baixa"]=scan(token,[-9.140,38.707,-9.134,38.713],2)
    positive=any(r["unique_images_lower_bound"]>0 for r in controls.values())
    out={"pilot":pilot,"controls":controls,"positive_control":positive,"interpretation":"pilot_query_validated" if positive else "inconclusive_no_positive_control"}
    Path("mapillary-coverage.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({"pilot":pilot["unique_images_lower_bound"],"controls":{k:v["unique_images_lower_bound"] for k,v in controls.items()},"positive_control":positive}))
    if not positive:raise SystemExit("No positive control; cannot confirm zero pilot coverage")
if __name__=="__main__":main()
