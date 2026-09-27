/* Versioned replay saves. Restore into a separate world before replacing the active run. */
(function(root){
  const E=root.MaleCNSEco || (require('./engine.js'),globalThis.MaleCNSEco);
  const VERSION=1,MAX_TICKS=5000,MAX_ACTIONS=5000;
  function fail(){throw new Error('This save is invalid or incompatible with this game version.');}
  function exportRun(w){
    if(w.tick>MAX_TICKS || w.inputLog.length>MAX_ACTIONS)throw new Error('Save limit: 5,000 ticks and 5,000 watering actions per run.');
    return JSON.parse(JSON.stringify({format:'malecns-run',version:VERSION,circuit:JSON.stringify(w.graph),
      mode:w.mission?.kind || 'sandbox',seed:w.seed,settings:w.initialSettings,rules:w.rules,
      tick:w.tick,actions:w.inputLog}));
  }
  function createRestorer(graph,data){
    if(!data || data.format!=='malecns-run' || data.version!==VERSION || data.circuit!==JSON.stringify(graph) ||
      !['sandbox','refuge','productivity'].includes(data.mode) || !Number.isInteger(data.seed) ||
      Math.abs(data.seed)>2147483647 || !Number.isInteger(data.tick) || data.tick<0 || data.tick>MAX_TICKS ||
      !Array.isArray(data.actions) || data.actions.length>MAX_ACTIONS ||
      !data.settings || typeof data.settings!=='object' || Array.isArray(data.settings))fail();
    const allowed=new Set(Object.keys(E.rulesFrom({})));
    if(Object.entries(data.settings).some(([k,v])=>!allowed.has(k) ||
      !(typeof v==='boolean' || (typeof v==='number' && Number.isFinite(v)))))fail();
    const w=data.mode==='sandbox'?E.createWorld(graph,data.settings,data.seed):E.createMission(graph,data.mode);
    if(w.seed!==data.seed || JSON.stringify(w.rules)!==JSON.stringify(data.rules) || data.tick<w.tick ||
      (w.mission && data.tick>w.mission.end))fail();
    let previous=w.tick;
    for(const a of data.actions){
      if(!a || !Number.isInteger(a.tick) || a.tick<previous || a.tick>data.tick ||
        !Number.isInteger(a.patch) || a.patch<0 || !Number.isFinite(a.amount) || a.amount<=0 || a.amount>.25)fail();
      previous=a.tick;
    }
    let index=0,done=false;
    return {world:w,get done(){return done;},advance(budget=100){
      if(!Number.isInteger(budget) || budget<1 || budget>1000)fail();
      for(let n=0;n<budget && !done;n++){
        while(index<data.actions.length && data.actions[index].tick===w.tick){
          const a=data.actions[index++],paid=E.waterGarden(w,a.patch);
          if(paid<=0 || Math.abs(paid-a.amount)>1e-10)fail();
        }
        if(w.tick===data.tick){done=true;break;}
        const before=w.tick;E.step(w);if(w.tick===before)fail();
      }
      return done;
    }};
  }
  root.MaleCNSSaves={exportRun,createRestorer,VERSION,MAX_TICKS};
})(typeof window!=='undefined'?window:globalThis);
