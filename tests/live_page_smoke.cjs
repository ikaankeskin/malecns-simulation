// Synthetic DOM/canvas harness: exercises wiring, not browser layout or biology.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('docs/index.html','utf8');
const elements = new Map();
const context = new Proxy({}, {get:(target,key) => target[key] || (()=>{}), set:(target,key,value)=>(target[key]=value,true)});
for (const match of html.matchAll(/<[^>]*\bid="([^"]+)"[^>]*>/g)) {
  const tag = match[0];
  elements.set(match[1], {value:tag.match(/\bvalue="([^"]+)"/)?.[1] || '', checked:tag.includes(' checked'),
    textContent:'', innerHTML:'', width:960, height:720, clientWidth:960, clientHeight:720,
    addEventListener(){}, getContext(){return context;}});
}
elements.get('preset').value='balanced'; elements.get('season-length').value='400'; elements.get('sense-range').value='24';
let interval;
const sandbox = {console, document:{getElementById(id){assert.ok(elements.has(id),id);return elements.get(id);},querySelectorAll(){return[];}},
  setInterval(fn){interval=fn;return 1;},clearInterval(){},
  fetch:async()=>({ok:true,json:async()=>JSON.parse(fs.readFileSync('demo.json','utf8'))})};
sandbox.window=sandbox; sandbox.addEventListener=()=>{};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('docs/social.js','utf8'),sandbox);
vm.runInContext(fs.readFileSync('docs/gardening.js','utf8'),sandbox);
vm.runInContext(fs.readFileSync('docs/engine.js','utf8'),sandbox);
const script = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n');
vm.runInContext(script,sandbox);
setImmediate(()=>{
  assert.equal(typeof interval,'function');
  elements.get('gifts-enabled').checked=true;
  elements.get('reciprocity').checked=true;
  elements.get('apply').onclick();
  assert.equal(vm.runInContext('world.rules.reciprocity',sandbox),true);
  assert.match(elements.get('sel-helpers').textContent,/No recent/);
  elements.get('gifts-enabled').checked=false;
  elements.get('reciprocity').checked=false;
  elements.get('apply').onclick();
  interval();
  assert.match(elements.get('season-banner').textContent,/Bloom/);
  elements.get('step').onclick();
  assert.equal(elements.get('play').textContent,'Play');
  const paused=elements.get('tick').textContent; interval();
  assert.equal(elements.get('tick').textContent,paused);
  elements.get('communication').checked=false;
  elements.get('seasons').checked=false; elements.get('scavenging').checked=false;
  elements.get('apply').onclick();
  assert.match(elements.get('season-banner').textContent,/Stable/);
  elements.get('play').onclick();
  for(let i=0;i<250;i++) interval();
  assert.ok(Number(elements.get('tick').textContent)>900);
  assert.equal(elements.get('scavenged').textContent,0);
  assert.equal(elements.get('signal-count').textContent,'0 / 0');
  elements.get('communication').checked=true;
  elements.get('social-learning').checked=false;
  elements.get('apply').onclick();
  assert.match(elements.get('sel-relationships').textContent,/Learning disabled/);
  elements.get('social-learning').checked=true;
  elements.get('apply').onclick();
  assert.match(elements.get('sel-relationships').textContent,/No arrival evidence/);
  elements.get('seasons').checked=true; elements.get('scavenging').checked=true;
  elements.get('season-length').value='200'; elements.get('apply').onclick();
  for(let i=0;i<151;i++) interval();
  assert.match(elements.get('season-banner').textContent,/Recovery/);
  console.log('Live page wiring, pause, step, restart and ecology toggles passed.');
  elements.get('garden-world').onclick();
  assert.equal(vm.runInContext('world.rules.map_half',sandbox),80);
  assert.equal(vm.runInContext('world.patches.length',sandbox),96);
  assert.equal(vm.runInContext('world.agents.length',sandbox),24);
  assert.equal(vm.runInContext('world.rules.gardening',sandbox),true);
  elements.get('camera').value='4';elements.get('camera').onchange();
  assert.equal(vm.runInContext('cameraBounds.max-cameraBounds.min',sandbox),42);
  elements.get('step').onclick();
  assert.match(elements.get('garden-stats').textContent,/gardens/);
  elements.get('reset').onclick();
  assert.equal(vm.runInContext('selectedPatch',sandbox),null);
});
