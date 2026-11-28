import {chromium} from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import {driveTerrainRoute} from './terrain-drive.mjs';
const root=process.env.MAPSLOP_RESULTS;
const file=path.join(root,'browser-report.json');
let report=fs.existsSync(file)?JSON.parse(fs.readFileSync(file,'utf8')):{success:false};
if(report.longDrive?.vertical_metrics&&report.longDrive50?.vertical_metrics){console.log('Both speeds already measured');process.exit(0);}
const b=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
  const page=await b.newPage({viewport:{width:1280,height:720}});
  await page.goto(process.env.MAPSLOP_TEST_URL,{waitUntil:'load',timeout:90000});
  await page.waitForFunction(()=>window.mapslop?.ready===true,{},{timeout:120000});
  let reference=null;
  const f=process.env.MAPSLOP_ROUTE_REFERENCE;
  if(f&&fs.existsSync(f))reference=JSON.parse(fs.readFileSync(f,'utf8')).longDrive?.route||null;
  if(!report.longDrive?.vertical_metrics){
    try{report.longDrive=await page.evaluate(driveTerrainRoute,{reference,targetSpeed:5.5});report.drive_diagnostic_fallback=true;}
    catch(e){report.drive_diagnostic_failure=String(e);}
  }
  // Same route even if either speed fails. Never relabel low-speed output as 50 km/h.
  reference=reference||report.longDrive?.route||null;
  if(reference&&!report.longDrive50?.vertical_metrics){
    try{report.longDrive50=await page.evaluate(driveTerrainRoute,{reference,targetSpeed:14});}
    catch(e){report.longDrive50={success:false,reason:String(e),target_speed_m_s:14};}
  }else if(!reference)report.longDrive50={success:false,reason:'Reference route unavailable',target_speed_m_s:14};
}catch(e){report.drive_diagnostic_failure=String(e);}
finally{
  fs.writeFileSync(file,JSON.stringify(report,null,2));
  console.log(JSON.stringify({vertical:report.longDrive?.vertical_metrics,reason:report.longDrive?.reason,error:report.drive_diagnostic_failure,drive50:{reason:report.longDrive50?.reason,max_speed_m_s:report.longDrive50?.max_speed_m_s,reached_target_speed:report.longDrive50?.reached_target_speed,vertical:report.longDrive50?.vertical_metrics}}));
  await b.close();
}
