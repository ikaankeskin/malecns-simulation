/* Shared nutrient cells, proportional allocation before any patch grows. */
(function(root){
  const Water=root.MaleCNSWater || (typeof require==='function'?(require('./water.js'),globalThis.MaleCNSWater):null);
  const RECOVERY=.0008,CROP_COST=.6,COMPOST=.3;
  function create(rules,seed=0){
    if(!rules.soil_limits)return null;
    const n=Math.ceil(2*rules.map_half/10);
    const result={n,half:rules.map_half,size:2*rules.map_half/n,cells:Array(n*n).fill(1),
      recovered:0,consumed:0,composted:0,recovery_per_tick:RECOVERY,crop_cost:CROP_COST,corpse_return:COMPOST};
    if(rules.water)result.water=Water.create(result,seed);return result;
  }
  function cellIndex(soil,x,y){
    const col=Math.max(0,Math.min(soil.n-1,Math.floor((x+soil.half)/soil.size)));
    const row=Math.max(0,Math.min(soil.n-1,Math.floor((y+soil.half)/soil.size)));
    return row*soil.n+col;
  }
  function growthBudget(soil,patches,growth,rules,tick=0){
    const rates={};if(!soil)return rates;
    Water.advance(soil,tick,rules);
    soil.cells.forEach((v,i)=>{const added=Math.min(RECOVERY,1-v);soil.cells[i]+=added;soil.recovered+=added;});
    const demands=new Map();
    [...patches].sort((a,b)=>a.id-b.id).forEach(p=>{
      if(p.stage!=='growing')return;
      const i=cellIndex(soil,p.x,p.y),d=Math.min(Math.max(0,p.timer),growth)*CROP_COST/rules.grow_ticks;
      if(!demands.has(i))demands.set(i,[]);demands.get(i).push([p,d]);
    });
    demands.forEach((rows,i)=>{
      const requested=rows.reduce((s,r)=>s+r[1],0);let fraction=requested?Math.min(1,soil.cells[i]/requested):1;
      const w=soil.water;
      if(w && requested)fraction=Math.min(fraction,w.moisture[i]/(requested*Water.CROP_WATER/CROP_COST));
      if(w){const drawn=requested*fraction*Water.CROP_WATER/CROP_COST;w.moisture[i]=Math.max(0,w.moisture[i]-drawn);w.uptake+=drawn;}
      const spent=requested*fraction;soil.cells[i]=Math.max(0,soil.cells[i]-spent);soil.consumed+=spent;
      rows.forEach(([p,d])=>{const paid=d*fraction;rates[p.id]=fraction===1?Math.min(Math.max(0,p.timer),growth):paid*rules.grow_ticks/CROP_COST;p.soil_uptake=(p.soil_uptake||0)+paid;});
    });return rates;
  }
  function compost(soil,corpse,tick,events){
    const i=cellIndex(soil,corpse.x,corpse.y),gain=Math.min(COMPOST,1-soil.cells[i]);
    if(gain<=0)return false;
    soil.cells[i]+=gain;soil.composted+=gain;
    events.push({tick,kind:'composted',agent:corpse.id,cell:i,x:corpse.x,y:corpse.y,nutrients:gain,
      text:'F'+corpse.id+' returned '+gain.toFixed(3)+' nutrients to soil cell '+i});return true;
  }
  function observe(soil,patches,tick){
    if(!soil)return;
    patches.forEach(p=>{
      const i=cellIndex(soil,p.x,p.y);p.soil_cell=i;p.fertility=soil.cells[i];
      if(soil.water)p.moisture=soil.water.moisture[i];
      if(!p.soil_history)p.soil_history=[];
      if(!p.soil_history.length || tick-p.soil_history[p.soil_history.length-1].tick>=100){
        p.soil_history.push({tick,cell:i,fertility:soil.cells[i]});p.soil_history=p.soil_history.slice(-6);
      }
    });
  }
  function snapshot(soil,patches){
    if(!soil)return null;
    const occupied=[...new Set(patches.map(p=>cellIndex(soil,p.x,p.y)))];
    return {...soil,...(soil.water?{water:JSON.parse(JSON.stringify(soil.water))}:{}),cells:[...soil.cells],occupied_cells:occupied.length,
      occupied_mean:occupied.reduce((s,i)=>s+soil.cells[i],0)/Math.max(1,occupied.length),
      depleted_cells:occupied.filter(i=>soil.cells[i]<.2).length};
  }
  root.MaleCNSSoil={create,cellIndex,growthBudget,compost,observe,snapshot};
})(typeof window!=='undefined'?window:globalThis);
