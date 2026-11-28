// MapSlop P0: north-up location map and independent pointer driving controls.
export function installPedomeUI(GEO, controllers, spawn, cameras) {
  const style=document.createElement('style');
  style.textContent=
  "#status{max-width:calc(100vw - 210px);font-size:13px;pointer-events:none}"+
  "#hud-map{position:fixed;top:10px;right:10px;z-index:4;width:172px;background:#13202bef;border:1px solid #ffffff45;border-radius:13px;padding:6px;box-sizing:border-box;box-shadow:0 4px 14px #0004}"+
  "#hud-map canvas{width:158px;height:158px;border-radius:8px;display:block}"+
  "#hud-map button{width:100%;padding:6px;font-size:12px;margin-top:3px}"+
  "#hud-map.expanded{width:min(90vw,70vh,520px);top:50%;right:50%;transform:translate(50%,-50%)}"+
  "#hud-map.expanded canvas{width:100%;height:auto;aspect-ratio:1}"+
  "#location{position:fixed;z-index:2;top:59px;left:10px;background:#13202bdc;padding:7px 10px;border-radius:9px;max-width:calc(100vw - 215px);font-size:12px;pointer-events:none}"+
  "#drive-ui{position:fixed;left:12px;right:12px;bottom:max(48px,env(safe-area-inset-bottom));z-index:5;display:flex;justify-content:space-between;align-items:flex-end;pointer-events:none;user-select:none;touch-action:none}"+
  "#drive-ui .group{display:flex;gap:10px;align-items:flex-end;pointer-events:auto;touch-action:none}"+
  "#drive-ui button,#hud-map button,#reset-car{font:600 15px system-ui;color:white;border:1px solid #ffffff65;border-radius:14px;background:#13202bdc;touch-action:none;cursor:pointer}"+
  "#drive-ui button{width:66px;height:66px;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:2px}"+
  "#drive-ui button b{font-size:26px;line-height:1}#drive-ui button span{font-size:10px}"+
  "#drive-ui button.active{background:#1485b8;box-shadow:inset 0 0 0 2px #fff8}"+
  "#reset-car{position:fixed;left:10px;top:102px;z-index:5;padding:8px 12px;font-size:12px}"+
  "#credits{max-width:calc(100vw - 36px);font-size:10px!important;padding:5px 8px!important;bottom:8px!important}"+
  "@media(max-height:450px){#hud-map{width:125px}#hud-map canvas{width:111px;height:111px}#hud-map.expanded canvas{width:100%;height:auto}#status,#location{max-width:calc(100vw - 155px)}#drive-ui button{width:55px;height:55px}#drive-ui{bottom:34px}#reset-car{top:93px}}"+
  "@media(max-width:400px) and (min-height:451px){#hud-map{width:140px}#hud-map canvas{width:126px;height:126px}#status,#location{max-width:calc(100vw - 166px)}#drive-ui button{width:60px;height:60px}#drive-ui .group{gap:6px}}";
  document.head.append(style);
  const loc=document.createElement('div'); loc.id='location'; loc.textContent='Pedome · Vila Nova de Famalicão';document.body.append(loc);
  const panel=document.createElement('section');panel.id='hud-map';panel.setAttribute('aria-label','Mapa de Pedome');
  panel.innerHTML='<canvas width="480" height="480" aria-label="Mapa com a posição do carro e da igreja"></canvas><button id="map-toggle" aria-expanded="false">Ampliar mapa</button>';
  document.body.append(panel);
  const canvas=panel.querySelector('canvas'), ctx=canvas.getContext('2d'), toggle=panel.querySelector('button');
  const reset=document.createElement('button');reset.id='reset-car';reset.textContent='↻ Repor carro';document.body.append(reset);
  const drive=document.createElement('div');drive.id='drive-ui';
  drive.innerHTML='<div class="group"><button data-drive="left" aria-label="Virar à esquerda"><b>←</b><span>Esquerda</span></button><button data-drive="right" aria-label="Virar à direita"><b>→</b><span>Direita</span></button></div><div class="group"><button data-drive="backward" aria-label="Travar ou marcha-atrás"><b>↓</b><span>Travão / ré</span></button><button data-drive="forward" aria-label="Acelerar"><b>↑</b><span>Acelerar</span></button></div>';
  document.body.append(drive);
  const buttons=[...drive.querySelectorAll('button')], pointers=new Map();
  function sync(){
    for(const b of buttons){
      const pressed=[...pointers.values()].includes(b);
      b.classList.toggle('active',pressed);
      b.setAttribute('aria-pressed',String(pressed));
      controllers.setTouchInput(b.dataset.drive,pressed?1:0);
    }
  }
  function release(e){if(pointers.delete(e.pointerId))sync();}
  function clear(){pointers.clear();sync();}
  for(const b of buttons){
    b.addEventListener('pointerdown',e=>{if(e.button!==0)return;e.preventDefault();e.stopPropagation();pointers.set(e.pointerId,b);b.setPointerCapture(e.pointerId);sync();});
    for(const type of ['pointerup','pointercancel','lostpointercapture'])b.addEventListener(type,release);
    b.addEventListener('contextmenu',e=>e.preventDefault());
  }
  window.addEventListener('blur',clear);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)clear();});
  reset.addEventListener('click',()=>{clear();controllers.teleportActiveTo(...spawn);});
  function expand(){const on=panel.classList.toggle('expanded');toggle.textContent=on?'Fechar mapa':'Ampliar mapa';toggle.setAttribute('aria-expanded',String(on));draw();}
  toggle.addEventListener('click',expand);
  window.addEventListener('keydown',e=>{if(e.code==='KeyM'&&!e.repeat)expand();});
  const {x0,x1,z0,z1}=GEO.frame.extent;
  const span=Math.max(x1-x0,z1-z0), scale=444/span;
  const X=x=>240+(x-(x0+x1)/2)*scale,Z=z=>240+(z-(z0+z1)/2)*scale;
  const background=document.createElement('canvas');background.width=background.height=480;const bg=background.getContext('2d');
  function path(c,pts,close=false){if(!pts||pts.length<4)return false;c.beginPath();c.moveTo(X(pts[0]),Z(pts[1]));for(let i=2;i<pts.length;i+=2)c.lineTo(X(pts[i]),Z(pts[i+1]));if(close)c.closePath();return true;}
  bg.fillStyle='#3b5141';bg.fillRect(0,0,480,480);
  for(const a of GEO.areas||[]){if(path(bg,a.ring,true)){bg.fillStyle=a.kind==='water'?'#427ea5':'#597450';bg.fill();}}
  for(const b of GEO.buildings||[]){if(path(bg,b.ring,true)){bg.fillStyle='#c4b7a1';bg.fill();}}
  bg.lineCap='round';bg.lineJoin='round';
  for(const r of GEO.roads){if(path(bg,r.pts)){bg.strokeStyle='#27343a';bg.lineWidth=Math.max(2.5,r.w*scale+2);bg.stroke();}}
  for(const r of GEO.roads){if(path(bg,r.pts)){bg.strokeStyle=r.kind==='footway'||r.kind==='path'?'#98a995':'#e1e3d9';bg.lineWidth=Math.max(1,r.w*scale);bg.stroke();}}
  for(const r of GEO.rivers||[]){if(path(bg,r.pts)){bg.strokeStyle='#62b1db';bg.lineWidth=3;bg.stroke();}}
  bg.strokeStyle='#fff7';bg.lineWidth=2;bg.setLineDash([5,5]);bg.strokeRect(X(x0),Z(z0),(x1-x0)*scale,(z1-z0)*scale);bg.setLineDash([]);
  // Origin is the documented coordinate of the parish church, not the car spawn.
  bg.fillStyle='#f5d47c';bg.beginPath();bg.arc(X(0),Z(0),7,0,Math.PI*2);bg.fill();
  bg.strokeStyle='#182026';bg.lineWidth=4;bg.font='bold 14px system-ui';bg.strokeText('Igreja de Pedome',X(0)+10,Z(0)-9);bg.fillText('Igreja de Pedome',X(0)+10,Z(0)-9);
  bg.fillStyle='white';bg.font='bold 22px system-ui';bg.fillText('N ↑',15,30);
  bg.strokeStyle='white';bg.lineWidth=2;bg.beginPath();bg.moveTo(15,450);bg.lineTo(15+100*scale,450);bg.stroke();bg.font='14px system-ui';bg.fillText('100 m',15,468);
  function closest(x,z){
    let best=Infinity, name='';
    for(const r of GEO.roads){
      if(!r.name&&!r.ref)continue;
      const p=r.pts;
      for(let i=2;i<p.length;i+=2){const ax=p[i-2],az=p[i-1],dx=p[i]-ax,dz=p[i+1]-az;const t=Math.max(0,Math.min(1,((x-ax)*dx+(z-az)*dz)/(dx*dx+dz*dz||1)));const d=(x-ax-t*dx)**2+(z-az-t*dz)**2;if(d<best){best=d;name=r.name||r.ref;}}
    }
    return best<3600?name:'Zona de Pedome';
  }
  function draw(){
    const e=controllers.getActiveEntity(),{x,z}=e.position;
    ctx.drawImage(background,0,0);
    ctx.save();ctx.translate(Math.max(10,Math.min(470,X(x))),Math.max(10,Math.min(470,Z(z))));ctx.rotate(-e.heading+Math.PI);
    ctx.beginPath();ctx.moveTo(0,-12);ctx.lineTo(8,8);ctx.lineTo(0,4);ctx.lineTo(-8,8);ctx.closePath();ctx.fillStyle='#22e8ff';ctx.strokeStyle='#06222e';ctx.lineWidth=3;ctx.fill();ctx.stroke();ctx.restore();
    const lat=GEO.frame.lat0-z/111060,lon=GEO.frame.lon0+x/(111320*Math.cos(GEO.frame.lat0*Math.PI/180));
    loc.textContent=closest(x,z)+' · '+Math.round(Math.hypot(x,z))+' m da igreja';
    loc.title=lat.toFixed(5)+', '+lon.toFixed(5)+' (aprox.)';
    canvas.dataset.playerX=String(x);canvas.dataset.playerZ=String(z);
  }
  let last=-Infinity;
  draw();
  return {update(now){if(now-last>200){last=now;draw();}},refresh:draw,clear};
}
