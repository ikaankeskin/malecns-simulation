/* Engineered local signals and bounded memory; no language model or biological claim. */
(function(root) {
  const DEFAULTS = {communication:true,signal_range:18,signal_ticks:24,signal_cooldown:60,signal_cost:.01,memory_ticks:180};
  const distance=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
  function initialize(a) {
    a.memories ||= []; a.social_history ||= []; a.last_signal ??= -1e9;
    a.social ||= {sent:0,received:0,followed:0,meals:0,empty:0,expired:0};
  }
  function willing(a,tick,gene) {
    const salt=gene==='signalling'?37:71;
    return (((a.id+1)*137+tick*53+salt)%1009)/1009 < (a.genome[gene] ?? .5);
  }
  function rememberEvent(a,tick,outcome,m,events) {
    const row={tick,kind:'signal_'+outcome,agent:a.id,source:m.source,x:m.x,y:m.y,
      text:'F'+a.id+': '+outcome+' after food signal from F'+m.source};
    a.social_history=[...a.social_history,{...row}].slice(-6); events.push(row);
  }
  function beginTick(agents,patches,signals,tick,rules,events) {
    signals.splice(0,signals.length,...signals.filter(s=>s.until>tick));
    for(const a of agents) {
      initialize(a); a.meal_position=null;
      if(!rules.communication || !a.alive) {a.memories=[];continue;}
      for(const m of a.memories) if(m.until<=tick && m.followed) {
        a.social.expired++; rememberEvent(a,tick,'expired',m,events);
      }
      a.memories=a.memories.filter(m=>m.until>tick);
    }
    if(!rules.communication) {signals.length=0;return;}
    const fresh=[];
    for(const a of agents.slice().sort((a,b)=>a.id-b.id)) {
      if(!a.alive || tick-a.last_signal<rules.signal_cooldown) continue;
      const visible=patches.filter(p=>p.stage==='mature' && distance(a,p)<rules.sense_range);
      if(!visible.length || a.energy<rules.signal_cost+.2) continue;
      a.last_signal=tick;
      if(!willing(a,tick,'signalling')) continue;
      visible.sort((p,q)=>distance(a,p)-distance(a,q)||p.id-q.id);
      const p=visible[0]; a.energy-=rules.signal_cost; a.social.sent++;
      fresh.push({id:tick+':'+a.id,source:a.id,x:p.x,y:p.y,origin_x:a.x,origin_y:a.y,
        patch:p.id,tick,until:tick+rules.signal_ticks});
      events.push({tick,kind:'signal_sent',agent:a.id,x:a.x,y:a.y,text:'F'+a.id+' signalled food at patch '+p.id});
    }
    signals.push(...fresh);
    for(const a of agents) {
      if(!a.alive) continue;
      for(const s of fresh) {
        if(a.id===s.source || Math.hypot(a.x-s.origin_x,a.y-s.origin_y)>rules.signal_range) continue;
        a.social.received++;
        if(!willing(a,tick+s.source,'responsiveness')) continue;
        if(a.memories.some(m=>m.source===s.source && m.x===s.x && m.y===s.y)) continue;
        if(a.memories.length>=4) {
          const index=a.memories.findIndex(m=>!m.followed);
          if(index<0) continue;
          a.memories.splice(index,1);
        }
        a.memories.push({...s,until:tick+rules.memory_ticks,followed:false});
      }
    }
  }
  function selectTarget(a,direct,tick,rules,events) {
    const memories=rules.communication?(a.memories||[]).map(m=>({...m,kind:'following_signal'})):[];
    const options=[...memories,...direct.filter(p=>distance(a,p)<rules.sense_range)];
    options.sort((p,q)=>distance(a,p)-distance(a,q));
    const choice=options[0]||null;
    if(choice && choice.kind==='following_signal') {
      const m=a.memories.find(m=>m.id===choice.id);
      if(!m.followed) {m.followed=true;a.social.followed++;rememberEvent(a,tick,'followed',m,events);}
    }
    return choice;
  }
  function endTick(agents,tick,rules,events) {
    for(const a of agents) {
      const target=a.target;
      if(!a.alive || !target || target.kind!=='following_signal') continue;
      const m=a.memories.find(m=>m.id===target.id);
      if(!m || distance(a,m)>=rules.eat_radius) continue;
      const outcome=a.meal_position && distance(a.meal_position,m)<1e-6?'meals':'empty';
      a.social[outcome]++;rememberEvent(a,tick,outcome,m,events);
      a.memories=a.memories.filter(x=>x.id!==m.id);
    }
  }
  function totals(agents) {
    return Object.fromEntries(['sent','received','followed','meals','empty','expired'].map(k=>[k,agents.reduce((n,a)=>n+(a.social?.[k]||0),0)]));
  }
  root.MaleCNSSocial={DEFAULTS,initialize,willing,beginTick,selectTarget,endTick,totals};
})(typeof window!=='undefined'?window:globalThis);
