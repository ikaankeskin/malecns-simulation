// Deterministic game balancing fixtures; no biological or general survival claim.
const assert=require('node:assert/strict');
require('../docs/engine.js');const E=globalThis.MaleCNSEco,graph=require('../circuits/dng13.json');
const reports={};
for(const policy of ['none','steady','late']){
  const w=E.createMission(graph,'productivity');
  assert.equal(w.tick,800);assert.equal(E.snapshot(w).environment.name,'Drought');
  assert.equal(w.mission.matured.length,0);assert.equal(E.thirstyGarden(w),null);
  while(w.tick<1200){
    if(policy==='steady' && w.tick%20===0){const id=E.thirstyGarden(w);if(id!=null)E.waterGarden(w,id);}
    if(policy==='late' && w.tick===1199)for(const p of w.patches.filter(p=>p.planter!=null))E.waterGarden(w,p.id);
    E.step(w);
  }
  const r=w.mission.result;reports[policy]={...r,status:w.mission.status,matured:w.mission.matured};
  assert.equal(w.mission.status,policy==='steady'?'won':'lost');
  assert.equal(r.productive,policy==='steady'?2:0);
  assert.equal(r.productive,new Set(w.mission.matured.map(p=>p.patch)).size);
  assert.equal(r.alive,24);assert.equal(r.waterUsed,policy==='none'?0:3);
  const frozen=JSON.stringify(w.mission);E.step(w);assert.equal(JSON.stringify(w.mission),frozen);
  assert.equal(E.waterGarden(w,w.patches.at(-1).id),0);
}
assert.throws(()=>E.createMission(graph,'invalid'),/Unknown mission/);
console.log(JSON.stringify(reports));
