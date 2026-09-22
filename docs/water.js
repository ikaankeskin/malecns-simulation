/* Toy water budgets, not fluid dynamics. */
(function(root){
  const CROP_WATER=.3,RAIN=[.0018,.0007,0,.001],EVAP=[.0007,.0009,.0022,.0007],FLOW=[1,.8,.12,.6];
  function create(s,seed){
    const half=s.half,phase=((seed%997)+997)%997*.017;
    const riverX=y=>half*(.35*Math.sin(3*y/half+phase)+.12*Math.sin(7*y/half+phase));
    const river=Array.from({length:65},(_,i)=>{const y=-half+2*half*i/64;return{x:riverX(y),y};});
    const banks=Array.from({length:s.n*s.n},(_,i)=>{const x=-half+(i%s.n+.5)*s.size,y=-half+(Math.floor(i/s.n)+.5)*s.size;return Math.max(0,1-Math.abs(x-riverX(y))/(s.size*.75+2));});
    return {moisture:banks.map(b=>.45+.45*b),banks,river,rain:0,river_input:0,evaporated:0,uptake:0,irrigated:0,reserve:3,crop_water:CROP_WATER,flow:1,weather:'rain'};
  }
  function advance(s,tick,rules){
    const w=s?.water;if(!w)return;
    const season=rules.seasons?Math.floor(tick/rules.season_length)%4:1;
    w.flow=FLOW[season];w.weather=['rain','light rain','drought','returning rain'][season];
    w.moisture.forEach((v,i)=>{
      const rain=Math.min(RAIN[season],1-v);v+=rain;w.rain+=rain;
      const river=Math.min(.006*w.banks[i]*FLOW[season],1-v);v+=river;w.river_input+=river;
      const loss=Math.min(EVAP[season],v);v-=loss;w.evaporated+=loss;w.moisture[i]=v;
    });
    const old=[...w.moisture],n=s.n;
    old.forEach((v,i)=>{const adjacent=[];if(i%n<n-1)adjacent.push(i+1);if(i+n<old.length)adjacent.push(i+n);
      adjacent.forEach(j=>{const flux=.035*(v-old[j]);w.moisture[i]-=flux;w.moisture[j]+=flux;});});
  }
  function irrigate(s,index){
    const w=s?.water;if(!w || !Number.isInteger(index) || index<0 || index>=w.moisture.length)return 0;
    const amount=Math.min(.25,w.reserve,Math.max(0,1-w.moisture[index]));
    w.reserve-=amount;w.moisture[index]+=amount;w.irrigated+=amount;return amount;
  }
  root.MaleCNSWater={create,advance,irrigate,CROP_WATER};
})(typeof window!=='undefined'?window:globalThis);
