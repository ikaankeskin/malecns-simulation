/* Engineered seed dispersal; independent of neural topology. */
(function(root) {
  function onMeal(agent, patch, agents, tick, rules) {
    if (!rules.gardening) return;
    patch.harvests = (patch.harvests || 0) + 1;
    patch.recent_eaters = [...(patch.recent_eaters || []), {agent:agent.id, tick}].slice(-6);
    if (patch.planter != null) {
      const byId = new Map(agents.map(a => [a.id,a]));
      const pending = [...(agent.parents || [])], seen = new Set();
      while (pending.length) {
        const id = pending.pop();
        if (seen.has(id)) continue;
        seen.add(id); pending.push(...(byId.get(id)?.parents || []));
      }
      if (seen.has(patch.planter)) patch.descendant_meals = (patch.descendant_meals || 0) + 1;
      if (!byId.get(patch.planter)?.alive) patch.posthumous_meals = (patch.posthumous_meals || 0) + 1;
    }
    if (!agent.carried_seed) agent.carried_seed = {source_patch:patch.id, x:patch.x, y:patch.y,
      tick, until:tick+600, root_patch:patch.root_patch ?? patch.id,
      plant_generation:(patch.plant_generation || 0)+1};
  }
  function plantSeeds(agents, patches, tick, rules, events) {
    if (!rules.gardening) return;
    [...agents].sort((a,b)=>a.id-b.id).forEach(agent => {
      const seed = agent.carried_seed;
      if (!seed) return;
      if (!agent.alive || tick >= seed.until) {agent.carried_seed=null; return;}
      if (tick-seed.tick<20 || agent.energy<0.8) return;
      if (Math.hypot(agent.x-seed.x,agent.y-seed.y)<3) return;
      if (patches.some(p=>Math.hypot(agent.x-p.x,agent.y-p.y)<2)) return;
      if (patches.filter(p=>p.planter!=null).length>=64) return;
      if (Math.abs(agent.x)>rules.map_half || Math.abs(agent.y)>rules.map_half) return;
      const patch = {id:Math.max(-1,...patches.map(p=>p.id))+1,x:agent.x,y:agent.y,
        stage:'seed',timer:rules.seed_ticks,nutrition:1,consumed_by:null,
        planter:agent.id,planted_tick:tick,planter_generation:agent.generation || 0,
        parent_patch:seed.source_patch,root_patch:seed.root_patch,plant_generation:seed.plant_generation,
        harvests:0,descendant_meals:0,posthumous_meals:0,recent_eaters:[]};
      patches.push(patch); agent.energy-=0.08; agent.carried_seed=null;
      agent.planted=(agent.planted || 0)+1;
      events.push({tick,kind:'planted',agent:agent.id,patch:patch.id,x:patch.x,y:patch.y,
        text:'F'+agent.id+' planted garden P'+patch.id+' from P'+patch.parent_patch});
    });
  }
  function totals(patches) {
    const gardens=patches.filter(p=>p.planter!=null);
    const result={planted:gardens.length,mature:gardens.filter(p=>p.stage==='mature').length};
    ['harvests','descendant_meals','posthumous_meals'].forEach(k=>result[k]=gardens.reduce((s,p)=>s+(p[k]||0),0));
    return result;
  }
  root.MaleCNSGardening={onMeal,plantSeeds,totals};
})(typeof window !== 'undefined' ? window : globalThis);
