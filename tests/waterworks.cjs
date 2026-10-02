// Synthetic construction budgets and game tuning, not biological validation.
const assert=require('node:assert/strict');require('../docs/saves.js');
const E=globalThis.MaleCNSEco,S=globalThis.MaleCNSSaves,W=globalThis.MaleCNSWater,g=require('../circuits/dng13.json');
const reports={};
for(const policy of ['none','early','planned','late']){
  const w=E.createMission(g,'builder');assert.equal(w.tick,600);
  if(policy!=='none'){
    const before=JSON.stringify(w);assert.equal(E.buildWaterworks(w,'reservoir',0).ok,false);assert.equal(JSON.stringify(w),before);
    assert.ok(E.buildWaterworks(w,'reservoir',137).ok);
    assert.equal(E.buildWaterworks(w,'reservoir',137).ok,false);
    assert.equal(E.buildWaterworks(w,'channel',0).ok,false);
    assert.ok(E.buildWaterworks(w,'channel',135).ok);assert.equal(w.soil.water.works.points,2);
    assert.equal(E.buildWaterworks(w,'channel',134).ok,false);
  }
  while(w.tick<1200){
    if(w.tick===({early:600,planned:1000,late:1199}[policy]))assert.ok(E.setWaterValve(w,true));
    E.step(w);
    const a=w.soil.water.works;
    if(a){assert.ok(a.stored>=0 && a.stored<=8);assert.ok(Math.abs(a.collected-a.stored-a.delivered-a.evaporated)<1e-9);}
    assert.ok(w.soil.water.moisture.every(x=>x>=-1e-12 && x<=1+1e-12));
    if(policy==='planned' && w.tick===1080){
      const r=S.createRestorer(g,S.exportRun(w));while(!r.done)r.advance();assert.deepEqual(E.snapshot(r.world),E.snapshot(w));
      assert.deepEqual(r.world.mission,w.mission);assert.deepEqual(r.world.inputLog,w.inputLog);
      for(let i=0;i<10;i++){E.step(r.world);E.step(w);}assert.deepEqual(E.snapshot(r.world),E.snapshot(w));
    }
  }
  assert.equal(w.mission.status,policy==='planned'?'won':'lost');
  reports[policy]={...w.mission.result,status:w.mission.status};
  const before=JSON.stringify(w);E.step(w);assert.equal(E.setWaterValve(w,false),false);assert.equal(E.buildWaterworks(w,'reservoir',137).ok,false);assert.equal(JSON.stringify(w),before);
  const r=S.createRestorer(g,S.exportRun(w));while(!r.done)r.advance();assert.deepEqual(E.snapshot(r.world),E.snapshot(w));
}
const sandbox=E.createWorld(g,{water:true,gardening:true,map_half:80},4);
assert.ok(E.buildWaterworks(sandbox,'reservoir',137).ok);assert.ok(E.buildWaterworks(sandbox,'channel',135).ok);
assert.ok(E.setWaterValve(sandbox,true));assert.equal(E.setWaterValve(sandbox,true),false);
const bad=S.exportRun(sandbox);bad.actions[1].cell=0;assert.throws(()=>{const r=S.createRestorer(g,bad);while(!r.done)r.advance();},/invalid/);
const legacy=E.createMission(g,'refuge'),v1=S.exportRun(legacy);v1.version=1;const r=S.createRestorer(g,v1);r.advance();assert.deepEqual(E.snapshot(r.world),E.snapshot(legacy));
assert.equal(E.buildWaterworks(legacy,'reservoir',137).ok,false);
console.log(JSON.stringify(reports));
