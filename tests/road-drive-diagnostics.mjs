import {chromium} from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import {driveTerrainRoute} from './terrain-drive.mjs';
const root=process.env.MAPSLOP_RESULTS;
const file=path.join(root,'browser-report.json');
let report=fs.existsSync(file)?JSON.parse(fs.readFileSync(file,'utf8')):{success:false};
if(report.longDrive?.vertical_metrics){console.log('Drive already measured');process.exit(0);}
const b=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
  const page=await b.newPage({viewport:{width:1280,height:720}});
  await page.goto(process.env.MAPSLOP_TEST_URL,{waitUntil:'load',timeout:90000});
  await page.waitForFunction(()=>window.mapslop?.ready===true,{},{timeout:120000});
  let reference=null;
  const f=process.env.MAPSLOP_ROUTE_REFERENCE;
  if(f&&fs.existsSync(f))reference=JSON.parse(fs.readFileSync(f,'utf8')).longDrive?.route||null;
  report.longDrive=await page.evaluate(driveTerrainRoute,{reference});
  report.drive_diagnostic_fallback=true;
}catch(e){report.drive_diagnostic_failure=String(e);}
finally{
  fs.writeFileSync(file,JSON.stringify(report,null,2));
  console.log(JSON.stringify({vertical:report.longDrive?.vertical_metrics,reason:report.longDrive?.reason,error:report.drive_diagnostic_failure}));
  await b.close();
}
