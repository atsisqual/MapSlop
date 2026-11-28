import {chromium} from 'playwright';
const url=process.env.MAPSLOP_TEST_URL;
const b=await chromium.launch({headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
 const page=await b.newPage({viewport:{width:823,height:384}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('console',m=>{if(m.type()==='error'&&!m.text().includes('favicon'))errors.push(m.text())});
 await page.route('**/*',r=>r.request().url().startsWith(new URL(url).origin+'/')?r.continue():r.abort());
 await page.goto(url,{waitUntil:'load',timeout:90000});
 await page.waitForFunction(()=>window.mapslop?.ready&&window.buildingDetailReport&&window.mapslop.orthoPreview?.ortho.report().settled,{},{timeout:120000});
 const s=await page.evaluate(()=>{const m=window.mapslop,p=m.controllers.getActiveEntity().position;return {buildings:m.GEO.buildings.length,estimated:m.GEO.buildings.filter(b=>b.est).length,measured:window.buildingDetailReport.measured,foundations:window.buildingDetailReport.foundation_failures.length,trees:m.vegetationPreview.vegetation.stats.total,tile:m.orthoPreview.ortho.inspect(p.x,p.z),stream:m.orthoPreview.ortho.report()}});
 if(s.buildings!==527||s.estimated!==156||s.measured!==17||s.foundations||s.trees!==5702||!s.tile?.applied||s.tile.level!=='near'||s.stream.errors.length||errors.length)throw Error(JSON.stringify({s,errors}));
 console.log('PAGES_COMBINED_PASS: 371 real heights, 156 estimated; '+JSON.stringify(s));
}finally{await b.close();}
