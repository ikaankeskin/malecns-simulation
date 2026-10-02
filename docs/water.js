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
    const works=w.works;
    if(works?.reservoir!=null){
      const gain=season===2?0:Math.min(8-works.stored,.08*w.banks[works.reservoir]*FLOW[season]);
      works.stored+=gain;works.collected+=gain;
      const loss=Math.min(works.stored,.0005);works.stored-=loss;works.evaporated+=loss;
      works.lastDelivery=0;
      if(works.open && works.path.length){
        const cell=works.path.at(-1),paid=Math.min(.035,works.stored,Math.max(0,.45-w.moisture[cell]));
        works.stored-=paid;works.delivered+=paid;works.lastDelivery=paid;w.moisture[cell]+=paid;
      }
    }
  }
  function irrigate(s,index){
    const w=s?.water;if(!w || !Number.isInteger(index) || index<0 || index>=w.moisture.length)return 0;
    const amount=Math.min(.25,w.reserve,Math.max(0,1-w.moisture[index]));
    w.reserve-=amount;w.moisture[index]+=amount;w.irrigated+=amount;return amount;
  }
  function route(s,from,to){
    const path=[];let row=Math.floor(from/s.n),col=from%s.n;
    const endRow=Math.floor(to/s.n),endCol=to%s.n;
    while(col!==endCol){col+=Math.sign(endCol-col);path.push(row*s.n+col);}
    while(row!==endRow){row+=Math.sign(endRow-row);path.push(row*s.n+col);}
    return path;
  }
  function preview(s,kind,cell){
    const w=s?.water,a=w?.works;
    const reject=reason=>({ok:false,reason,path:[],cost:0});
    if(!w)return reject('Start a garden world with rivers and soil enabled.');
    if(!Number.isInteger(cell) || cell<0 || cell>=s.n*s.n)return reject('Select a soil cell inside the map.');
    if(kind==='reservoir'){
      if(a?.reservoir!=null)return reject('Only one reservoir per run.');
      if(w.banks[cell]<.3)return reject('Reservoirs need a riverbank cell (outlined blue).');
      return {ok:true,cost:2,path:[cell],reason:'Riverbank reservoir · 2 building points'};
    }
    if(kind!=='channel')return reject('Choose a reservoir or channel.');
    if(a?.reservoir==null)return reject('Build a riverbank reservoir first.');
    if(a.path.length)return reject('One channel per run. Retry to try another route.');
    const path=route(s,a.reservoir,cell);
    if(!path.length || path.length>4)return reject('Choose an outlet 1–4 cells from the reservoir.');
    if(path.length>a.points)return reject('Not enough building points for this route.');
    return {ok:true,cost:path.length,path,reason:path.length+' channel cells · '+path.length+' building points'};
  }
  function build(s,kind,cell){
    const p=preview(s,kind,cell);if(!p.ok)return p;
    const w=s.water;
    if(kind==='reservoir')w.works={reservoir:cell,path:[],points:4,stored:0,collected:0,delivered:0,evaporated:0,lastDelivery:0,open:false};
    else {w.works.path=p.path;w.works.points-=p.cost;}
    return p;
  }
  root.MaleCNSWater={create,advance,irrigate,preview,build,CROP_WATER};
})(typeof window!=='undefined'?window:globalThis);
