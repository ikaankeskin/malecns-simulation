// Synthetic game rules and deterministic scenario checks; not biological validation.
const assert=require('node:assert/strict');
require('../docs/engine.js');const E=globalThis.MaleCNSEco;
const graph=require('../circuits/dng13.json');
const baseline=E.createMission(graph);
while(baseline.tick<1200)E.step(baseline);
assert.equal(baseline.mission.status,'lost');
assert.equal(baseline.mission.result.refuges,0);
const retry=E.createMission(graph);
while(retry.tick<1199)E.step(retry);
const cells=new Set();
for(const p of retry.patches.filter(p=>p.planter!=null)){
  const cell=globalThis.MaleCNSSoil.cellIndex(retry.soil,p.x,p.y);
  if(cells.has(cell))continue;
  E.waterGarden(retry,p.id);cells.add(cell);
  if(cells.size===3)break;
}
E.step(retry);
assert.equal(retry.mission.status,'won');
assert.equal(retry.mission.actions.length,3);
assert.equal(retry.mission.result.waterUsed,.75);
const frozen=JSON.stringify(E.snapshot(retry));E.step(retry);
assert.equal(JSON.stringify(E.snapshot(retry)),frozen);
assert.equal(E.waterGarden(retry,retry.patches.at(-1).id),0);
const fresh=E.createMission(graph);assert.equal(fresh.tick,0);assert.equal(fresh.soil.water.reserve,3);
for(const a of fresh.agents)a.alive=false;
E.step(fresh);assert.equal(fresh.mission.status,'lost');assert.equal(fresh.tick,1);
console.log(JSON.stringify({baseline:baseline.mission.result,watered:retry.mission.result}));
