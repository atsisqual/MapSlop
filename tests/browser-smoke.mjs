import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
const target=process.env.MAPSLOP_TEST_URL || 'http://127.0.0.1:8080/?webgl';
const origin=new URL(target).origin+'/';
const results=process.env.MAPSLOP_RESULTS || '/tmp/pedome-results';
fs.mkdirSync(results,{recursive:true});
const browser=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1280,height:720}});
const errors=[], consoleLog=[], failed=[];
page.on('pageerror',e=>errors.push(e.message));
page.on('console',m=>consoleLog.push({type:m.type(),text:m.text()}));
page.on('requestfailed',r=>failed.push({url:r.url(),error:r.failure()?.errorText}));
page.on('response',r=>{if(r.status()>=400)failed.push({url:r.url(),status:r.status()})});
// All runtime assets should be local; fail unexpected external requests rather than depending on CDN.
await page.route('**/*',r=>r.request().url().startsWith(origin)?r.continue():r.abort());
let report={errors,consoleLog,failed};
try {
  await page.goto(target,{waitUntil:'load',timeout:90000});
  await page.waitForFunction(()=>window.mapslop?.ready===true,{},{timeout:120000});
  const state=()=>page.evaluate(()=>{const e=window.mapslop.controllers.getActiveEntity();return {mode:window.mapslop.controllers.activeMode,x:e.position.x,y:e.position.y,z:e.position.z,speed:e.speed,heading:e.heading,status:document.querySelector('#status').textContent,canvas:!!document.querySelector('canvas'),roads:window.mapslop.GEO.roads.length,buildings:window.mapslop.GEO.buildings.length}});
  report.before=await state();
  await page.screenshot({path:path.join(results,'pedome-start.png'),timeout:60000});
  await page.keyboard.down('w');
  try { await page.waitForFunction(()=>Math.abs(window.mapslop.controllers.getActiveEntity().speed)>1,{},{timeout:60000}); await page.waitForFunction(({x,z})=>{const p=window.mapslop.controllers.getActiveEntity().position;return Math.hypot(p.x-x,p.z-z)>2;},report.before,{timeout:90000}); } finally { await page.keyboard.up('w'); }
  report.after=await state();
  report.distance=Math.hypot(report.after.x-report.before.x,report.after.z-report.before.z);
  await page.screenshot({path:path.join(results,'pedome-driving.png'),timeout:60000});
  if(report.before.mode!=='car'||!report.before.canvas||report.before.roads!==179||report.before.buildings!==527||!Number.isFinite(report.distance)||report.distance<=2||errors.length||consoleLog.some(m=>m.type==='error'||/GL_INVALID_OPERATION|GL_INVALID_FRAMEBUFFER_OPERATION|shader error/i.test(m.text))||failed.some(r=>!r.url.endsWith('/favicon.ico')))throw Error('Browser driving validation failed');
  // Verify mobile-sized layout, map position, pointer input and release.
  await page.setViewportSize({width:823,height:384});
  await page.locator('#reset-car').click();
  await page.waitForFunction(()=>Math.abs(window.mapslop.controllers.getActiveEntity().speed)<0.1);
  const forward=page.locator('[data-drive="forward"]');
  const bounds=await forward.boundingBox();
  if(!bounds||!(await page.locator('#hud-map canvas').isVisible())||await page.locator('#drive-ui button').count()!==4)throw Error('Missing mobile HUD');
  const left=page.locator('[data-drive="left"]');
  const lb=await left.boundingBox();
  if(!lb)throw Error('Steering control missing');
  const cdp=await page.context().newCDPSession(page);
  await cdp.send('Emulation.setTouchEmulationEnabled',{enabled:true,maxTouchPoints:5});
  const pedal={x:Math.round(bounds.x+bounds.width/2),y:Math.round(bounds.y+bounds.height/2),id:1};
  const steer={x:Math.round(lb.x+lb.width/2),y:Math.round(lb.y+lb.height/2),id:2};
  try {
    await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[pedal]});
    await page.waitForFunction(()=>window.mapslop.controllers.getActiveEntity().speed>1,{},{timeout:60000});
    await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[pedal,steer]});
    await page.waitForFunction(()=>['forward','left'].every(a=>document.querySelector('[data-drive="'+a+'"]').getAttribute('aria-pressed')==='true'),{},{timeout:15000});
    report.touchSpeed=await page.evaluate(()=>window.mapslop.controllers.getActiveEntity().speed);
    report.multiTouch=true;
  } finally {
    await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  }
  await page.waitForFunction(()=>['forward','left'].every(a=>document.querySelector('[data-drive="'+a+'"]').getAttribute('aria-pressed')==='false'),{},{timeout:15000});
  report.touchRelease=true;
  await cdp.detach();
  await page.locator('#map-toggle').click();
  if(await page.locator('#map-toggle').getAttribute('aria-expanded')!=='true')throw Error('Map expansion failed');
  await page.locator('#map-toggle').click();
  report.location=await page.locator('#location').textContent();
  await page.screenshot({path:path.join(results,'pedome-mobile.png'),timeout:60000});
  if(errors.length||consoleLog.some(m=>m.type==='error'||/GL_INVALID_OPERATION|GL_INVALID_FRAMEBUFFER_OPERATION|shader error/i.test(m.text)))throw Error('HUD validation failed');
  report.success=true;
} catch(e) {
  report.success=false; report.error=e.message;
  report.status=await page.locator('#status').textContent({timeout:5000}).catch(()=>null);
  await page.screenshot({path:path.join(results,'failure.png'),timeout:30000}).catch(()=>{});
  throw e;
} finally {
  fs.writeFileSync(path.join(results,'browser-report.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
  await browser.close();
}
