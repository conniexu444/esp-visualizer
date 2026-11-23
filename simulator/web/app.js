'use strict';
const el = id => document.getElementById(id);
const source = el('source'), lcd = el('lcd'), log = el('log');
const ctx = lcd.getContext('2d'), image = ctx.createImageData(240,240);
let worker, input, generation = 0, demoSource, compiledSource = null, pending;
const draftKey = 'roundbench.sketch.v1';
function persist() {
  try { localStorage.setItem(draftKey, JSON.stringify({name:el('name').textContent, source:source.value})); }
  catch { el('revision').textContent = 'Use Save .ino to keep edits'; }
}
function status(label, state) {
  el('status').textContent = label;
  el('status').dataset.state = state;
}
function append(text) {
  const follow = log.scrollTop + log.clientHeight >= log.scrollHeight - 5;
  log.textContent = (log.textContent + text).slice(-24000);
  if (follow) log.scrollTop = log.scrollHeight;
}
function highlight() {
  const code = source.value;
  const pattern = /\/\*[\s\S]*?(?:\*\/|$)|\/\/[^\n]*|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|#[a-z]+|\b(?:const|constexpr|void|char|int|long|float|double|bool|return|if|for|while|else|uint\d+_t|unsigned|static|class|true|false)\b|\b(?:0x[0-9a-fA-F]+|\d+(?:\.\d+)?)\b/g;
  const frag = document.createDocumentFragment();
  let last = 0;
  for (const match of code.matchAll(pattern)) {
    frag.append(code.slice(last,match.index));
    const token = match[0], span = document.createElement('span');
    span.className = token[0]==='/' ? 'comment' : /["']/.test(token[0]) ? 'str' : /^\d/.test(token) ? 'num' : 'kw';
    span.textContent = token;
    frag.append(span);
    last = match.index + token.length;
  }
  frag.append(code.slice(last)+'\n');
  el('highlight').replaceChildren(frag);
  el('lines').textContent = code.split('\n').map((_,i)=>i+1).join('\n')+'\n';
  syncScroll();
}
function syncScroll() {
  el('highlight').scrollTop = el('lines').scrollTop = source.scrollTop;
  el('highlight').scrollLeft = source.scrollLeft;
}
function setSource(name, value) {
  source.value = value;
  el('name').textContent = name;
  source.scrollTop = source.scrollLeft = 0;
  highlight();
  persist();
  el('revision').textContent = '';
}
function stop() {
  ++generation;
  pending?.abort();
  worker?.terminate();
  worker = input = null;
  el('stop').disabled = true;
  el('run').disabled = false;
  el('position').textContent = 'X —   Y —';
}
function paint(buffer) {
  const pixels = new Uint16Array(buffer);
  for (let i=0;i<pixels.length;i++) {
    const v=pixels[i], j=i*4;
    image.data[j]=(v>>11)*255/31;
    image.data[j+1]=((v>>5)&63)*255/63;
    image.data[j+2]=(v&31)*255/31;
    image.data[j+3]=255;
  }
  ctx.putImageData(image,0,0);
}
async function run() {
  stop();
  const id=generation, code=source.value;
  status('Compiling','building');
  el('stop').disabled=false;
  el('run').disabled=true;
  log.textContent='';
  ctx.clearRect(0,0,240,240);
  pending=new AbortController();
  const fail = message => {
    if(id!==generation) return;
    stop();
    status('Error','error');
    append(message+'\n');
  };
  try {
    if (!window.crossOriginIsolated) throw Error('Open the loopback URL from Open Visualizer.command in a browser that supports shared memory.');
    const response=await fetch('/compile',{method:'POST',headers:{'Content-Type':'text/plain'},body:code,signal:pending.signal});
    if(!response.ok) throw Error(await response.text());
    const binary=await response.arrayBuffer();
    if(id!==generation) return;
    const memory=new SharedArrayBuffer(8);
    input=new Int32Array(memory);
    worker=new Worker('/runner.js');
    worker.onmessage=({data})=>{
      if(id!==generation) return;
      if(data.ready){
        status('Running','running');
        compiledSource=code;
        el('revision').textContent=source.value!==code?'Edits pending':'';
        el('run').disabled=false;
      }
      if(data.frame) paint(data.frame);
      if(data.serial) append(data.serial);
      if(data.error) fail(data.error);
    };
    worker.onerror=event=>fail(event.message);
    worker.postMessage({binary,input:memory},[binary]);
  } catch(error) { fail(error.message); }
}
function touch(event, down) {
  const rect=lcd.getBoundingClientRect();
  const x=Math.max(0,Math.min(239,Math.floor((event.clientX-rect.left)*240/rect.width)));
  const y=Math.max(0,Math.min(239,Math.floor((event.clientY-rect.top)*240/rect.height)));
  const pressed=down && Math.hypot(x-119.5,y-119.5)<=120;
  el('position').textContent='X '+String(x).padStart(3,'0')+'   Y '+String(y).padStart(3,'0');
  if(input) Atomics.store(input,0,(pressed?65536:0)|(x<<8)|y);
}
lcd.onpointerdown=e=>{if(e.isPrimary){lcd.setPointerCapture(e.pointerId);touch(e,true);}};
lcd.onpointermove=e=>{if(e.isPrimary) touch(e,!!(e.buttons&1));};
lcd.onpointerup=e=>{if(e.isPrimary) touch(e,false);};
lcd.onlostpointercapture=lcd.onpointercancel=()=>{if(input) Atomics.and(input,0,65535);};
source.oninput=()=>{highlight();persist();el('revision').textContent=source.value===compiledSource?'':'Edits pending';};
source.onscroll=syncScroll;
source.onkeydown=e=>{
  if(e.key==='Tab' && !e.shiftKey){
    e.preventDefault(); source.setRangeText('  ',source.selectionStart,source.selectionEnd,'end'); source.oninput();
  }
};
document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key==='Enter'){e.preventDefault();run();}});
el('run').onclick=run;
el('stop').onclick=()=>{stop();status('Stopped','idle');};
el('clear').onclick=()=>{log.textContent='';};
el('save').onclick=()=>{
  const a=document.createElement('a');
  const url=URL.createObjectURL(new Blob([source.value],{type:'text/plain'}));
  a.href=url;a.download=el('name').textContent;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
function replaceSketch(name,code) {
  if(source.value!==demoSource && source.value!==code &&
    !confirm('Replace the editor contents? Use Save .ino first to keep a copy.')) return;
  stop();setSource(name,code);status('Ready','idle');ctx.clearRect(0,0,240,240);log.textContent='';
}
el('file').onchange=async e=>{
  const file=e.target.files[0];
  if(file) replaceSketch(file.name,await file.text());
  e.target.value='';
};
el('demo').onclick=()=>{replaceSketch('TouchDial.ino',demoSource);if(source.value===demoSource) run();};
(async()=>{
  try{
    const response=await fetch('/TouchDial.ino');
    if(!response.ok) throw Error('Could not load the touch demo.');
    demoSource=await response.text();
    let draft;
    try { draft=JSON.parse(localStorage.getItem(draftKey)); } catch {}
    if(draft && typeof draft.source==='string' && typeof draft.name==='string'){
      setSource(draft.name,draft.source);
      if(draft.source===demoSource) run(); else append('Sketch restored. Select Run sketch to start.\n');
    }else { setSource('TouchDial.ino',demoSource);run(); }
  } catch(error) { status('Error','error');append(error.message); }
})();
