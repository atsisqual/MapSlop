import {chromium} from 'playwright';
import fs from 'node:fs';
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const root=process.env.MAPSLOP_RESULTS;
let report={pass:false};
try{
  const page=await browser.newPage({viewport:{width:1280,height:720}});
  await page.goto(process.env.MAPSLOP_TEST_URL,{waitUntil:'load',timeout:90000});
  await page.waitForFunction(()=>window.mapslop?.ready===true&&window.buildingDetailReport,{},{timeout:120000});
  report=await page.evaluate(()=>window.buildingDetailReport);
  report.valid_foundations=report.rows.every(r=>Number.isFinite(r.foundation_min_m)&&r.terrain_max_m>=r.foundation_min_m&&r.roof_top_m>=r.habitable_base_m);
  report.no_points_fallback=[1446763703,1460484467].every(id=>report.rows.some(r=>String(r.osm_id)===String(id)&&r.policy!=='roofer_lod22'));
  report.pass=report.buildings===527&&report.measured===18&&report.valid_foundations&&report.no_points_fallback&&report.shell_triangles<=120000&&report.all_triangles<=250000&&report.building_draw_calls<=40;
  await page.screenshot({path:root+'/roof-preview.png',timeout:60000});
  // Visual inspection remains a manual review of the 20 buildings, not this count.
}catch(e){report.error=String(e);report.pass=false;}
finally{fs.writeFileSync(root+'/building-detail-report.json',JSON.stringify(report,null,2));await browser.close();}
console.log(JSON.stringify({...report,rows:undefined}));
if(!report.pass)process.exitCode=1;
