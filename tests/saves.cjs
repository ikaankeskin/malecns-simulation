// Synthetic persistence tests, not biology validation.
const assert=require('node:assert/strict');require('../docs/saves.js');
const E=globalThis.MaleCNSEco,S=globalThis.MaleCNSSaves,g=require('../circuits/dng13.json');
function restore(data){const r=S.createRestorer(g,data);while(!r.done)r.advance(100);return r.world;}
function compare(a,b){assert.deepEqual(E.snapshot(a),E.snapshot(b));assert.deepEqual(a.mission,b.mission);assert.deepEqual(a.circuits,b.circuits);}
for(const mode of ['sandbox','refuge','productivity']){
  const w=mode==='sandbox'?E.createWorld(g,{agents:24,patches:96,map_half:80,gardening:true,water:true,hazards:false},4):E.createMission(g,mode);
  const target=w.tick+300;
  while(w.tick<target){if(w.tick%20===0){const id=E.thirstyGarden(w);if(id!=null)E.waterGarden(w,id);}E.step(w);}
  const saved=S.exportRun(w),r=restore(saved);compare(w,r);
  for(let i=0;i<20;i++){E.step(w);E.step(r);}compare(w,r);
  if(mode==='productivity'){
    const bad=structuredClone(saved);bad.actions[0].patch=999999;assert.throws(()=>restore(bad),/invalid/);
    const badAmount=structuredClone(saved);badAmount.actions[0].amount=.1;assert.throws(()=>restore(badAmount),/invalid/);
  }
}
const ended=E.createMission(g,'productivity');while(ended.tick<1200)E.step(ended);compare(ended,restore(S.exportRun(ended)));
const saved=S.exportRun(ended);
for(const change of [{version:99},{tick:5001},{seed:Infinity},{settings:{map_half:Infinity}},{mode:'x'},{actions:[{tick:799,patch:0,amount:.25}]}])assert.throws(()=>restore({...saved,...change}));
assert.throws(()=>S.createRestorer(require('../demo.json'),saved),/invalid/);
console.log('Save/resume: three modes, future trajectory, terminal state and invalid saves passed.');
