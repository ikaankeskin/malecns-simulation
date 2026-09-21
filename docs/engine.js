/* Live ecosystem engine. Dynamics are simulation abstractions; DNg13 topology is MaleCNS-derived. */
(function (root) {
  const Social = root.MaleCNSSocial || (typeof require === 'function' ? (require('./social.js'), globalThis.MaleCNSSocial) : null);
  const DEFAULTS = {
    agents: 8,
    patches: 8,
    map_half: 20,
    energy_start: 1,
    energy_max: 2,
    base_drain: 0.0012,
    move_cost: 0.003,
    meal: 0.55,
    eat_radius: 0.55,
    sense_range: 24,
    max_age: 520,
    seed_ticks: 12,
    grow_ticks: 40,
    cooldown_ticks: 50,
    corpse_ticks: 180,
    seasons: true, season_length: 400, scavenging: true,
    hazards: true, hazard_count: 3, hazard_radius: 3.5, hazard_drain: 0.02,
    gifts: false, gift_amount: 0.15, gift_keep: 0.1, gift_range: 4, gift_cooldown: 80, gift_chance: 0.25, gift_follow: 100,
    scavenge_below: 1.1, corpse_meal: 0.35, compost_radius: 5, compost_boost: 12,
    max_population: 48,
    mate_radius: 6,
    min_repro_age: 36,
    min_repro_energy: 1.05,
    repro_cost: 0.35,
    repro_cooldown: 40,
    offspring_energy: 0.8,
    food_rate: 1,
    aging_rate: 1,
    repro_rate: 1.2,
    mutation_rate: 0.9,
    mutation_sigma: 0.14,
    meal_life: 90,
    meal_life_cap: 900,
  };

  Object.assign(DEFAULTS, Social.DEFAULTS);

  const BASE_GENOME = {
    turn_gain: 1, sensory_gain: 1, metabolism: 1, speed: 1,
    lifespan: 1, fertility: 1, signalling: .5, responsiveness: .5, spot: 0, echo: 0, drift: 0,
  };
  const GENE_BOUNDS = {
    turn_gain: [0.45, 2], sensory_gain: [0.45, 2.2], metabolism: [0.5, 1.8], speed: [0.55, 1.9],
    signalling: [0, 1], responsiveness: [0, 1], lifespan: [0.65, 1.9], fertility: [0.6, 2.2], spot: [0, 1], echo: [0, 1], drift: [0, 1],
  };
  const MUTATION_LABELS = {
    speed: ['speed boost', 'sluggish'],
    lifespan: ['long life', 'short life'],
    fertility: ['litter +1', 'low fertility'],
    metabolism: ['hungry', 'thrifty'],
    sensory_gain: ['keen', 'dim'],
    turn_gain: ['sharp turn', 'wide turn'],
    spot: ['speckled', 'speckled'],
    echo: ['echo', 'echo'],
    drift: ['wobble', 'wobble'],
  };

  const PRESETS = {
    balanced: { agents: 8, patches: 6, food_rate: 1, aging_rate: 1, repro_rate: 1 },
    scarce: { agents: 10, patches: 3, food_rate: 0.55, aging_rate: 1.15, repro_rate: 0.55 },
    bloom: { agents: 6, patches: 10, food_rate: 1.85, aging_rate: 0.7, repro_rate: 1.7 },
    harsh: { agents: 12, patches: 4, food_rate: 0.65, aging_rate: 1.85, repro_rate: 0.35 },
  };

  const DECODER = { turn_sign: -1, turn_gain: 1, turn_clip: 0.3, speed_gain: 0.13, sensory_sign: 1 };

  function rng(seed) {
    let a = (seed >>> 0) || 1;
    return function () {
      a |= 0;
      a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function clamp(value, lo, hi) {
    return Math.max(lo, Math.min(hi, value));
  }

  function gauss(random, sigma) {
    let u = 0;
    let v = 0;
    while (u === 0) u = random();
    while (v === 0) v = random();
    return sigma * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }

  function inheritGenome(mother, father, random, rules) {
    const child = {};
    const mutations = {};
    const rate = rules.mutation_rate;
    const sigma = rules.mutation_sigma;
    Object.keys(GENE_BOUNDS).forEach((gene) => {
      const mid = 0.5 * (mother[gene] + father[gene]);
      let value = mid;
      if (rate > 0 && sigma > 0 && random() < rate) {
        const bounds = GENE_BOUNDS[gene];
        if (gene === 'spot' || gene === 'echo' || gene === 'drift' || gene === 'signalling' || gene === 'responsiveness') {
          value = clamp(mid + gauss(random, sigma), bounds[0], bounds[1]);
        } else {
          value = clamp(mid * (1 + gauss(random, sigma)), bounds[0], bounds[1]);
        }
      }
      child[gene] = value;
      if (Math.abs(value - mid) > 1e-6) mutations[gene] = value - mid;
    });
    return [child, mutations];
  }

  function describeMutations(mutations) {
    return Object.keys(mutations).map((gene) => {
      const labels = MUTATION_LABELS[gene] || [gene, gene];
      const delta = mutations[gene];
      if (gene === 'metabolism') return delta > 0 ? labels[0] : labels[1];
      return delta >= 0 ? labels[0] : labels[1];
    });
  }

  function lifespanOf(agent, rules) {
    const bonus = Math.min(rules.meal_life_cap, agent.meals * rules.meal_life);
    return Math.max(1, Math.round(rules.max_age * (agent.genome.lifespan || 1) + bonus));
  }

  function lineageTable(agents) {
    const table = {};
    agents.forEach((agent) => {
      const lid = agent.lineage;
      if (!table[lid]) table[lid] = { founder: lid, born: 0, living: 0, max_gen: 0, meals: 0, contested: 0, displaced: 0 };
      table[lid].born += 1;
      if (agent.alive) table[lid].living += 1;
      table[lid].max_gen = Math.max(table[lid].max_gen, agent.generation);
      table[lid].meals += agent.meals;
      table[lid].contested += agent.contested || 0;
      table[lid].displaced += agent.displaced || 0;
    });
    return table;
  }

  function livingByGen(agents) {
    const counts = {};
    agents.forEach((agent) => {
      if (!agent.alive) return;
      const key = String(agent.generation);
      counts[key] = (counts[key] || 0) + 1;
    });
    return counts;
  }

  function relocatePatch(patch, random, rules) {
    const half = rules.map_half * 0.82;
    patch.x = (random() * 2 - 1) * half;
    patch.y = (random() * 2 - 1) * half;
  }

  function decoderFor(base, genome) {
    return {
      turn_sign: base.turn_sign,
      turn_gain: base.turn_gain * genome.turn_gain,
      turn_clip: base.turn_clip,
      speed_gain: base.speed_gain * genome.speed,
      sensory_sign: base.sensory_sign,
    };
  }

  function rulesFrom(ui) {
    ['seasons', 'scavenging', 'communication', 'social_learning', 'hazards', 'gifts'].forEach(key => {
      if (ui[key] != null && typeof ui[key] !== 'boolean') throw new Error(key + ' must be boolean');
    });
    if (ui.season_length != null && (!Number.isInteger(ui.season_length) || ui.season_length < 1)) {
      throw new Error('season_length must be a positive integer');
    }
    if (ui.sense_range != null && (!Number.isFinite(ui.sense_range) || ui.sense_range <= 0)) throw new Error('sense_range must be positive');
    const food = Math.max(0.2, Number(ui.food_rate) || 1);
    const aging = Math.max(0.2, Number(ui.aging_rate) || 1);
    const repro = Math.max(0, Number(ui.repro_rate) || 0);
    const agents = clamp(Math.round(Number(ui.agents) || 8), 2, 24);
    const patches = clamp(Math.round(Number(ui.patches) || 6), 2, 12);
    return Object.assign({}, DEFAULTS, {
      communication: ui.communication == null ? true : ui.communication,
      social_learning: ui.social_learning == null ? true : ui.social_learning,
      sense_range: ui.sense_range == null ? DEFAULTS.sense_range : ui.sense_range,
      seasons: ui.seasons == null ? true : ui.seasons,
      scavenging: ui.scavenging == null ? true : ui.scavenging,
      hazards: ui.hazards == null ? true : ui.hazards,
      gifts: ui.gifts == null ? false : ui.gifts,
      season_length: ui.season_length == null ? DEFAULTS.season_length : ui.season_length,
      agents: agents,
      patches: patches,
      food_rate: food,
      aging_rate: aging,
      repro_rate: repro,
      seed_ticks: Math.max(4, Math.round(DEFAULTS.seed_ticks / food)),
      grow_ticks: Math.max(8, Math.round(DEFAULTS.grow_ticks / food)),
      cooldown_ticks: Math.max(12, Math.round(DEFAULTS.cooldown_ticks / food)),
      max_age: Math.max(80, Math.round(DEFAULTS.max_age / aging)),
      repro_enabled: repro > 0,
      repro_cooldown: repro <= 0 ? 1e9 : Math.max(12, Math.round(DEFAULTS.repro_cooldown / repro)),
      min_repro_energy: repro <= 0 ? 99 : Math.max(0.55, DEFAULTS.min_repro_energy - 0.15 * (repro - 1)),
      mate_radius: repro <= 0 ? DEFAULTS.mate_radius : DEFAULTS.mate_radius * (0.75 + 0.25 * repro),
      max_population: clamp(Math.round(Number(ui.max_population) || 48), agents, 50),
      mutation_rate: clamp(Number(ui.mutation_rate == null ? DEFAULTS.mutation_rate : ui.mutation_rate), 0, 1),
      mutation_sigma: Math.max(0, Number(ui.mutation_sigma == null ? DEFAULTS.mutation_sigma : ui.mutation_sigma)),
      meal_life: DEFAULTS.meal_life,
      meal_life_cap: DEFAULTS.meal_life_cap,
    });
  }

  function Circuit(graph) {
    const nodes = graph.nodes;
    const ids = {};
    nodes.forEach((node, index) => { ids[String(node.id)] = index; });
    const incoming = nodes.map(() => []);
    graph.edges.forEach((edge) => {
      incoming[ids[String(edge.post)]].push([ids[String(edge.pre)], edge.weight / 100]);
    });
    this.nodes = nodes;
    this.incoming = incoming;
    this.activity = nodes.map(() => 0);
  }

  Circuit.prototype.step = function (drives) {
    const old = this.activity;
    this.activity = this.incoming.map((incoming, i) => {
      let sum = drives[i];
      for (let k = 0; k < incoming.length; k += 1) sum += old[incoming[k][0]] * incoming[k][1];
      return clamp(0.75 * old[i] + 0.25 * sum, 0, 1);
    });
    return this.activity;
  };

  Circuit.prototype.motors = function () {
    let left = 0;
    let right = 0;
    this.nodes.forEach((node, i) => {
      if (node.role !== 'motor') return;
      if (node.side === 'left') left += this.activity[i];
      if (node.side === 'right') right += this.activity[i];
    });
    return [left, right];
  };

  function sensoryDrives(nodes, decoder, bearing, stimulus) {
    const lateral = Math.sin(bearing);
    return nodes.map((node) => {
      if (node.role !== 'sensory') return 0;
      let laterality = 0;
      if (node.side === 'left') laterality = decoder.sensory_sign * lateral;
      else if (node.side === 'right') laterality = -decoder.sensory_sign * lateral;
      return stimulus * (1 + laterality);
    });
  }

  function integrateMotion(decoder, x, y, heading, left, right) {
    const turn = clamp((right - left) * decoder.turn_sign * decoder.turn_gain, -decoder.turn_clip, decoder.turn_clip);
    heading += turn;
    const speed = decoder.speed_gain * Math.min(1, left + right);
    return [x + speed * Math.cos(heading), y + speed * Math.sin(heading), heading, speed];
  }

  function nearest(x, y, points) {
    let best = null;
    let dist = Infinity;
    points.forEach((point) => {
      const d = Math.hypot(point[0] - x, point[1] - y);
      if (d < dist) { dist = d; best = point; }
    });
    return [best, dist];
  }

  function spawnAgents(count, radius, energy) {
    const agents = [];
    for (let i = 0; i < count; i += 1) {
      const angle = 2 * Math.PI * i / count;
      agents.push({
        id: i, x: radius * Math.cos(angle), y: radius * Math.sin(angle), heading: angle + Math.PI,
        energy: energy, age: 0, alive: true, meals: 0, ate: false, birth_tick: 0,
        death_tick: null, cause_of_death: null, corpse_until: null, last_repro: -1e6,
        generation: 0, parents: null, offspring: 0, left: 0, right: 0, speed: 0,
        genome: Object.assign({}, BASE_GENOME), mutations: {}, trail: [],
        lineage: i, contested: 0, displaced: 0,
      });
    }
    return agents;
  }

  function spawnPatches(count, radius, random, rules) {
    const patches = [];
    for (let i = 0; i < count; i += 1) {
      const mature = i % 2 === 0;
      const patch = {
        id: i, x: 0, y: 0,
        stage: mature ? 'mature' : 'growing',
        timer: mature ? 0 : Math.floor(rules.grow_ticks / 2),
        nutrition: 1, consumed_by: null,
      };
      relocatePatch(patch, random, rules);
      patches.push(patch);
    }
    return patches;
  }

  function advancePatch(patch, rules, random, growth = 1) {
    if (patch.stage === 'mature') return null;
    patch.timer -= growth;
    if (patch.timer > 0) return null;
    if (patch.stage === 'cooldown') {
      patch.stage = 'seed';
      patch.timer = rules.seed_ticks;
      patch.consumed_by = null;
      if (random) relocatePatch(patch, random, rules);
    } else if (patch.stage === 'seed') {
      patch.stage = 'growing';
      patch.timer = rules.grow_ticks;
    } else if (patch.stage === 'growing') {
      patch.stage = 'mature';
      patch.timer = 0;
      return 'food_mature';
    }
    return null;
  }

  const SEASONS = [['Bloom', 1.65], ['Abundance', 1], ['Drought', 0.3], ['Recovery', 0.8]];

  function seasonAt(tick, rules) {
    if (!rules.seasons) return {name: 'Stable', index: -1, growth: 1, progress: 0, remaining: 0, cycle: 0};
    const index = Math.floor(tick / rules.season_length) % SEASONS.length;
    return {name: SEASONS[index][0], index: index, growth: SEASONS[index][1],
      progress: (tick % rules.season_length) / rules.season_length,
      remaining: rules.season_length - tick % rules.season_length,
      cycle: Math.floor(tick / (rules.season_length * SEASONS.length)) + 1};
  }

  function corpseFreshness(agent, tick, rules) {
    if (agent.alive || agent.corpse_until == null || tick >= agent.corpse_until) return 0;
    return clamp((agent.corpse_until - tick) / rules.corpse_ticks, 0, 1);
  }

  function scavengeCorpses(agents, tick, rules, events) {
    if (!rules.scavenging) return 0;
    let count = 0;
    agents.slice().sort((a,b) => a.id-b.id).forEach(corpse => {
      const freshness = corpseFreshness(corpse, tick, rules);
      if (!freshness || corpse.death_tick >= tick) return;
      const eligible = agents.filter(a => a.alive && !a.ate && a.energy < rules.scavenge_below &&
        Math.hypot(a.x-corpse.x, a.y-corpse.y) < rules.eat_radius);
      eligible.sort((a,b) => Math.hypot(a.x-corpse.x,a.y-corpse.y)-Math.hypot(b.x-corpse.x,b.y-corpse.y) || a.id-b.id);
      const eater = eligible[0];
      if (!eater) return;
      const gain = Math.min(rules.energy_max-eater.energy, rules.corpse_meal*freshness);
      if (gain <= 0) return;
      eater.energy += gain; eater.ate = true; eater.scavenges = (eater.scavenges || 0)+1;
      corpse.corpse_until = null;
      events.push({tick: tick, kind: 'scavenged', agent: eater.id, corpse: corpse.id, energy: Number(gain.toFixed(6)),
        x: corpse.x, y: corpse.y, text: 'F'+eater.id+' scavenged F'+corpse.id+' (+'+gain.toFixed(2)+' energy)'});
      count += 1;
    });
    return count;
  }

  function compostCorpse(corpse, patches, tick, rules, events) {
    const growing = patches.filter(p => ['seed','growing'].includes(p.stage) &&
      Math.hypot(p.x-corpse.x,p.y-corpse.y) <= rules.compost_radius);
    growing.sort((a,b) => Math.hypot(a.x-corpse.x,a.y-corpse.y)-Math.hypot(b.x-corpse.x,b.y-corpse.y) || a.id-b.id);
    const patch = growing[0];
    if (!patch || rules.compost_boost <= 0) return false;
    patch.timer = Math.max(0,patch.timer-rules.compost_boost);
    events.push({tick:tick, kind:'composted', agent:corpse.id, patch:patch.id, x:patch.x, y:patch.y,
      text:'F'+corpse.id+' returned nutrients to patch '+patch.id});
    return true;
  }

  function spawnHazards(rules, seed) {
    if (!rules.hazards) return [];
    const radius = rules.hazard_radius;
    const span = Math.max(0, rules.map_half - radius);
    const discs = [];
    for (let index = 0; index < rules.hazard_count; index += 1) {
      const angle = (seed * 0.917 + index) * 2.399963;
      const ring = span * (0.45 + 0.5 * ((seed * 17 + index * 13) % 5) / 4);
      discs.push({
        id: index,
        x: Math.round(Math.max(-span, Math.min(span, ring * Math.cos(angle))) * 1e6) / 1e6,
        y: Math.round(Math.max(-span, Math.min(span, ring * Math.sin(angle))) * 1e6) / 1e6,
        radius: radius,
      });
    }
    return discs;
  }

  function nearestHazard(agent, hazards, rules) {
    let best = null;
    (hazards || []).forEach((disc) => {
      const dist = Math.hypot(agent.x - disc.x, agent.y - disc.y);
      if (dist <= disc.radius || dist < rules.sense_range) {
        const gap = dist - disc.radius;
        if (!best || gap < best.gap || (gap === best.gap && disc.id < best.disc.id)) best = { gap: gap, disc: disc, dist: dist };
      }
    });
    return best;
  }

  function avoidanceTarget(agent, disc) {
    let dx = agent.x - disc.x, dy = agent.y - disc.y;
    const dist = Math.hypot(dx, dy);
    if (dist < 1e-9) {
      dx = Math.cos(agent.heading + Math.PI); dy = Math.sin(agent.heading + Math.PI);
    } else {
      dx /= dist; dy /= dist;
    }
    return { x: agent.x + dx, y: agent.y + dy, kind: 'avoiding_hazard', id: disc.id };
  }

  function competeHazard(agent, choice, hazards, rules) {
    const sensed = rules.hazards ? nearestHazard(agent, hazards, rules) : null;
    if (!sensed) return choice;
    const food = choice ? Math.hypot(choice.x - agent.x, choice.y - agent.y) : Infinity;
    if (sensed.gap <= 0 || sensed.gap < food) return avoidanceTarget(agent, sensed.disc);
    return choice;
  }

  function initGifts(agent) {
    if (agent.last_gift == null) agent.last_gift = -1e9;
    ['gifts_sent', 'gifts_received', 'gift_paid', 'gift_gained', 'gift_alive_later', 'gift_checks'].forEach((key) => {
      if (agent[key] == null) agent[key] = 0;
    });
    if (!agent.gift_pending) agent.gift_pending = [];
  }

  function giftWilling(agent, tick, rules) {
    return ((agent.id + 1) * 137 + tick * 53 + 91) % 1009 / 1009 < rules.gift_chance;
  }

  function exchangeGifts(agents, tick, rules, events) {
    agents.forEach((agent) => {
      initGifts(agent);
      const pending = [];
      agent.gift_pending.forEach((row) => {
        if (tick < row.check) { pending.push(row); return; }
        const recipient = agents.find((other) => other.id === row.recipient);
        agent.gift_checks += 1;
        if (recipient && recipient.alive) agent.gift_alive_later += 1;
      });
      agent.gift_pending = pending;
    });
    if (!rules.gifts) return 0;
    let sent = 0;
    agents.filter((agent) => agent.alive).sort((a, b) => a.id - b.id).forEach((donor) => {
      if (tick - donor.last_gift < rules.gift_cooldown) return;
      if (donor.energy < rules.gift_amount + 0.2) return;
      const neighbours = agents.filter((other) => other.alive && other.id !== donor.id
        && Math.hypot(donor.x - other.x, donor.y - other.y) <= rules.gift_range);
      if (!neighbours.length) return;
      donor.last_gift = tick;
      if (!giftWilling(donor, tick, rules)) return;
      const recipient = neighbours.slice().sort((a, b) => Math.hypot(donor.x - a.x, donor.y - a.y) - Math.hypot(donor.x - b.x, donor.y - b.y) || a.id - b.id)[0];
      const gain = Math.max(0, Math.min(rules.energy_max - recipient.energy, rules.gift_keep));
      donor.energy -= rules.gift_amount;
      recipient.energy += gain;
      donor.gifts_sent += 1;
      donor.gift_paid += rules.gift_amount;
      recipient.gifts_received += 1;
      recipient.gift_gained += gain;
      donor.gift_pending.push({ tick: tick, recipient: recipient.id, check: tick + rules.gift_follow });
      sent += 1;
      events.push({ tick: tick, kind: 'gift', agent: donor.id, recipient: recipient.id,
        text: 'F' + donor.id + ' gave energy to F' + recipient.id });
    });
    return sent;
  }

  function giftTotals(agents) {
    agents.forEach(initGifts);
    return {
      sent: agents.reduce((sum, agent) => sum + agent.gifts_sent, 0),
      received: agents.reduce((sum, agent) => sum + agent.gifts_received, 0),
      energy_paid: agents.reduce((sum, agent) => sum + agent.gift_paid, 0),
      energy_gained: agents.reduce((sum, agent) => sum + agent.gift_gained, 0),
      alive_later: agents.reduce((sum, agent) => sum + agent.gift_alive_later, 0),
      checked: agents.reduce((sum, agent) => sum + agent.gift_checks, 0),
    };
  }

  function resolveDeath(agent, rules, inHazard, predation) {
    if (predation) return 'predation';
    if (inHazard && agent.energy <= 0) return 'hazard';
    if (agent.energy <= 0) return 'starvation';
    if (agent.age >= lifespanOf(agent, rules)) return 'old_age';
    return null;
  }

  function createWorld(graph, ui, seed) {
    const rules = rulesFrom(ui || {});
    const decoder = Object.assign({}, DECODER);
    const random = rng(seed);
    const world = {
      graph: graph,
      decoder: decoder,
      rules: rules,
      seed: seed,
      tick: 0,
      agents: spawnAgents(rules.agents, rules.map_half * 0.85, rules.energy_start),
      patches: spawnPatches(rules.patches, rules.map_half * 0.4, random, rules),
      hazards: spawnHazards(rules, seed),
      circuits: [],
      events: [], signals: [],
      births: 0, scavenged: 0, composted: 0,
      peak: rules.agents,
      contested: 0,
      displaced: 0,
      series: [],
      random: random,
    };
    for (let i = 0; i < world.agents.length; i += 1) world.circuits.push(new Circuit(graph));
    return world;
  }

  function kill(agent, tick, cause, corpseTicks) {
    agent.alive = false;
    agent.energy = 0;
    agent.death_tick = tick;
    agent.cause_of_death = cause;
    agent.corpse_until = tick + corpseTicks;
  }

  function canReproduce(agent, tick, rules) {
    return rules.repro_enabled && agent.alive && agent.age >= rules.min_repro_age
      && agent.energy >= rules.min_repro_energy && (tick - agent.last_repro) >= rules.repro_cooldown;
  }

  function reproduce(world) {
    const rules = world.rules;
    const tick = world.tick;
    if (!rules.repro_enabled) return;
    const candidates = world.agents.filter((agent) => canReproduce(agent, tick, rules)).sort((a, b) => a.id - b.id);
    const used = {};
    for (let i = 0; i < candidates.length; i += 1) {
      const parent = candidates[i];
      if (used[parent.id]) continue;
      let partner = null;
      let best = rules.mate_radius;
      for (let j = 0; j < candidates.length; j += 1) {
        const other = candidates[j];
        if (other.id <= parent.id || used[other.id]) continue;
        const distance = Math.hypot(parent.x - other.x, parent.y - other.y);
        if (distance < best) { best = distance; partner = other; }
      }
      if (!partner) continue;
      if (world.agents.filter((agent) => agent.alive).length >= rules.max_population) {
        world.events.push({ tick: tick, kind: 'repro_capped', text: 'population cap blocked a birth' });
        break;
      }
      used[parent.id] = true;
      used[partner.id] = true;
      parent.energy -= rules.repro_cost;
      partner.energy -= rules.repro_cost;
      parent.last_repro = tick;
      partner.last_repro = tick;
      parent.offspring += 1;
      partner.offspring += 1;
      const first = inheritGenome(parent.genome, partner.genome, world.random, rules);
      const extra = first[0].fertility >= 1.35 ? 1 : 0;
      for (let sibling = 0; sibling < 1 + extra; sibling += 1) {
        if (sibling && world.agents.filter((agent) => agent.alive).length >= rules.max_population) break;
        const inherited = sibling === 0 ? first : inheritGenome(parent.genome, partner.genome, world.random, rules);
        const angle = world.random() * 2 * Math.PI;
        const half = rules.map_half;
        const child = {
          id: world.agents.reduce((max, agent) => Math.max(max, agent.id), 0) + 1,
          x: clamp((parent.x + partner.x) / 2 + 0.35 * Math.cos(angle), -half, half),
          y: clamp((parent.y + partner.y) / 2 + 0.35 * Math.sin(angle), -half, half),
          heading: angle, energy: rules.offspring_energy, age: 0, alive: true, meals: 0, ate: false,
          birth_tick: tick, death_tick: null, cause_of_death: null, corpse_until: null,
          last_repro: tick, generation: Math.max(parent.generation, partner.generation) + 1,
          parents: [parent.id, partner.id], offspring: 0, left: 0, right: 0, speed: 0, trail: [],
          genome: inherited[0], mutations: inherited[1], lineage: parent.lineage, contested: 0, displaced: 0,
        };
        world.agents.push(child);
        world.circuits.push(new Circuit(world.graph));
        world.births += 1;
        if (sibling) { parent.offspring += 1; partner.offspring += 1; }
        const labels = describeMutations(inherited[1]);
        world.events.push({
          tick: tick, kind: 'born', agent: child.id, parents: child.parents, mutations: inherited[1],
          text: 'F' + child.id + ' born to F' + parent.id + ' and F' + partner.id + ' · ' +
            (labels.length ? labels.join(', ') : 'no mutation'),
        });
      }
    }
  }

  function step(world) {
    const rules = world.rules;
    const decoder = world.decoder;
    const environment = seasonAt(world.tick, rules);
    if (rules.seasons && world.tick % rules.season_length === 0) {
      world.events.push({tick: world.tick, kind: 'season', text: environment.name+': plant growth ×'+environment.growth.toFixed(2)});
    }
    Social.beginTick(world.agents, world.patches, world.signals, world.tick, rules, world.events);
    const edible = world.patches.filter(p => p.stage === 'mature').map(p => ({x:p.x, y:p.y, kind:'foraging'}));
    world.agents.forEach((agent, index) => {
      agent.ate = false;
      agent.speed = 0;
      if (!agent.alive) { agent.left = 0; agent.right = 0; return; }
      agent.age += 1;
      const options = edible.slice();
      if (rules.scavenging && agent.energy < rules.scavenge_below) {
        world.agents.forEach(a => { if (corpseFreshness(a,world.tick,rules)>0) options.push({x:a.x,y:a.y,kind:'scavenging',id:a.id}); });
      }
      options.sort((a,b) => Math.hypot(a.x-agent.x,a.y-agent.y)-Math.hypot(b.x-agent.x,b.y-agent.y));
      const choice = competeHazard(agent, Social.selectTarget(agent, options, world.tick, rules, world.events), world.hazards, rules);
      const found = choice ? [[choice.x,choice.y],Math.hypot(choice.x-agent.x,choice.y-agent.y)] : [null,Infinity];
      agent.intent = choice ? choice.kind : 'searching';
      agent.target = agent.intent !== 'searching' ? choice : null;
      let bearing = 0;
      let stimulus = 0;
      if (found[0]) {
        bearing = Math.atan2(found[0][1] - agent.y, found[0][0] - agent.x) - agent.heading;
        bearing = Math.atan2(Math.sin(bearing), Math.cos(bearing));
        stimulus = (choice.kind === 'following_signal' ? .5 : Math.max(0, 1 - found[1] / rules.sense_range)) * agent.genome.sensory_gain;
      }
      const circuit = world.circuits[index];
      const body = decoderFor(decoder, agent.genome);
      circuit.step(sensoryDrives(circuit.nodes, body, bearing, stimulus));
      const motors = circuit.motors();
      const moved = integrateMotion(body, agent.x, agent.y, agent.heading, motors[0], motors[1]);
      agent.x = moved[0]; agent.y = moved[1]; agent.heading = moved[2]; agent.speed = moved[3];
      const half = rules.map_half;
      if (Math.abs(agent.x)>half) {agent.x=clamp(agent.x,-half,half);agent.heading=Math.PI-agent.heading;}
      if (Math.abs(agent.y)>half) {agent.y=clamp(agent.y,-half,half);agent.heading=-agent.heading;}
      agent.heading += 0.01 * (agent.genome.drift || 0) * Math.sin(agent.age * 0.19);
      agent.left = motors[0]; agent.right = motors[1];
      agent.trail.push([agent.x, agent.y]);
      if (agent.trail.length > 90) agent.trail.shift();
    });
    const taken = {};
    world.patches.forEach((patch) => {
      if (patch.stage !== 'mature') {
        if (advancePatch(patch, rules, world.random, environment.growth) === 'food_mature') {
          world.events.push({ tick: world.tick, kind: 'food_mature', text: 'patch ' + patch.id + ' matured' });
        }
        return;
      }
      const contenders = world.agents.filter((agent) => agent.alive && !taken[agent.id]
        && Math.hypot(agent.x - patch.x, agent.y - patch.y) < rules.eat_radius);
      if (!contenders.length) return;
      const winner = contenders.reduce((best, agent) => agent.id < best.id ? agent : best);
      taken[winner.id] = true;
      if (contenders.length > 1) {
        world.contested += 1;
        winner.contested += 1;
        contenders.forEach((agent) => {
          if (agent.id === winner.id) return;
          agent.displaced += 1;
          world.displaced += 1;
        });
        world.events.push({ tick: world.tick, kind: 'contested',
          text: 'F' + winner.id + ' beat ' + (contenders.length - 1) + ' rival(s) to patch ' + patch.id });
      }
      winner.meal_position = {x:patch.x,y:patch.y};
      winner.ate = true;
      winner.meals += 1;
      winner.energy = Math.min(rules.energy_max, winner.energy + rules.meal * patch.nutrition);
      patch.stage = 'cooldown';
      patch.timer = rules.cooldown_ticks;
      patch.consumed_by = winner.id;
      world.events.push({ tick: world.tick, kind: 'ate', text: 'F' + winner.id + ' ate patch ' + patch.id });
    });
    Social.endTick(world.agents, world.tick, rules, world.events);
    exchangeGifts(world.agents, world.tick, rules, world.events);
    world.scavenged += scavengeCorpses(world.agents, world.tick, rules, world.events);
    reproduce(world);
    world.agents.forEach((agent) => {
      if (!agent.alive) return;
      agent.energy -= rules.base_drain * agent.genome.metabolism + rules.move_cost * agent.speed;
      const sensed = nearestHazard(agent, world.hazards, rules);
      const inHazard = !!(sensed && sensed.dist <= sensed.disc.radius);
      if (inHazard) agent.energy -= rules.hazard_drain;
      const cause = resolveDeath(agent, rules, inHazard, false);
      if (cause) {
        kill(agent, world.tick, cause, rules.corpse_ticks);
        const label = { hazard: 'died in a hazard', starvation: 'starved', old_age: 'died of old age', predation: 'was killed' }[cause];
        world.events.push({ tick: world.tick, kind: 'died', cause: cause, text: 'F' + agent.id + ' ' + label });
      }
    });
    world.agents.forEach((agent) => {
      if (agent.corpse_until != null && world.tick >= agent.corpse_until) {
        world.composted += Number(compostCorpse(agent, world.patches, world.tick, rules, world.events));
        world.events.push({ tick: world.tick, kind: 'corpse_decayed', text: 'F' + agent.id + ' corpse decayed' });
        agent.corpse_until = null;
      }
    });
    const alive = world.agents.filter((agent) => agent.alive).length;
    world.peak = Math.max(world.peak, alive);
    if (world.tick % 4 === 0) {
      const living = world.agents.filter((agent) => agent.alive);
      world.series.push({
        tick: world.tick,
        alive: alive,
        born: world.births,
        food: world.patches.filter((patch) => patch.stage === 'mature').length,
        energy: living.length ? living.reduce((sum, agent) => sum + agent.energy, 0) / living.length : 0,
        speed: living.length ? living.reduce((sum, agent) => sum + agent.genome.speed, 0) / living.length : 1,
        metabolism: living.length ? living.reduce((sum, agent) => sum + agent.genome.metabolism, 0) / living.length : 1,
        lifespan: living.length ? living.reduce((sum, agent) => sum + agent.genome.lifespan, 0) / living.length : 1,
        fertility: living.length ? living.reduce((sum, agent) => sum + agent.genome.fertility, 0) / living.length : 1,
        generation: living.length ? Math.max.apply(null, living.map((agent) => agent.generation)) : 0,
      });
      if (world.series.length > 180) world.series.shift();
    }
    if (world.events.length > 80) world.events.splice(0, world.events.length - 80);
    world.tick += 1;
    return world;
  }

  function snapshot(world) {
    const living = world.agents.filter((agent) => agent.alive);
    const generations = world.agents.map((agent) => agent.generation);
    return {
      tick: Math.max(0, world.tick - 1),
      alive: living.length,
      births: world.births,
      peak: world.peak,
      generation: generations.length ? Math.max.apply(null, generations) : 0,
      mature_food: world.patches.filter((patch) => patch.stage === 'mature').length,
      mean_energy: living.length ? living.reduce((sum, agent) => sum + agent.energy, 0) / living.length : 0,
      mean_speed: living.length ? living.reduce((sum, agent) => sum + agent.genome.speed, 0) / living.length : 1,
      mean_metabolism: living.length ? living.reduce((sum, agent) => sum + agent.genome.metabolism, 0) / living.length : 1,
      mean_lifespan: living.length ? living.reduce((sum, agent) => sum + agent.genome.lifespan, 0) / living.length : 1,
      mean_fertility: living.length ? living.reduce((sum, agent) => sum + agent.genome.fertility, 0) / living.length : 1,
      signals: world.signals, social: Social.totals(world.agents),
      environment: seasonAt(Math.max(0,world.tick-1),world.rules),
      scavenged: world.scavenged, composted: world.composted,
      contested: world.contested || 0,
      displaced: world.displaced || 0,
      hazards: world.hazards,
      hazard_deaths: world.agents.filter((agent) => agent.cause_of_death === 'hazard').length,
      gifts: giftTotals(world.agents),
      lineages: lineageTable(world.agents),
      living_by_gen: livingByGen(world.agents),
      corpses: world.agents.filter((agent) => !agent.alive && agent.corpse_until != null)
        .map(agent => Object.assign({}, agent, {freshness: corpseFreshness(agent, world.tick, world.rules)})),
      agents: world.agents,
      patches: world.patches,
      events: world.events,
      series: world.series,
      rules: world.rules,
      seed: world.seed,
    };
  }

  function randomize(randomFn) {
    const roll = randomFn || Math.random;
    const names = Object.keys(PRESETS);
    const preset = names[Math.floor(roll() * names.length)];
    return Object.assign({ preset: preset, seed: 1 + Math.floor(roll() * 9999) }, PRESETS[preset], {
      agents: 4 + Math.floor(roll() * 13),
      food_rate: Math.round((0.4 + roll() * 1.8) * 100) / 100,
      aging_rate: Math.round((0.45 + roll() * 1.7) * 100) / 100,
      repro_rate: Math.round((roll() * 2.1) * 100) / 100,
      mutation_rate: Math.round((0.4 + roll() * 0.6) * 100) / 100,
    });
  }

  function familyTree(rows, focus, tick, maxDepth) {
    if (maxDepth == null) maxDepth = 4;
    if (!Number.isInteger(maxDepth) || maxDepth < 0) throw new Error('max_depth must be a nonnegative integer');
    const present = [];
    (rows || []).forEach((row) => {
      if ((row.birth_tick || 0) > tick) return;
      const parents = row.parents ? row.parents.slice() : null;
      const dead = row.death_tick != null && row.death_tick <= tick;
      present.push({
        id: row.id, generation: row.generation || 0, parents: parents,
        alive: !dead, cause: dead ? (row.cause || row.cause_of_death || null) : null,
      });
    });
    const byId = {};
    present.forEach((row) => { byId[row.id] = row; });
    if (byId[focus] == null) return { focus: focus, depth: maxDepth, omitted: 0, nodes: [] };
    const children = {};
    present.forEach((row) => {
      (row.parents || []).forEach((parent) => {
        if (!children[parent]) children[parent] = [];
        if (children[parent].indexOf(row.id) < 0) children[parent].push(row.id);
      });
    });
    Object.keys(children).forEach((parent) => children[parent].sort((a, b) => a - b));
    const included = {};
    included[focus] = ['self', 0];
    function addLayer(frontier, direction) {
      const next = [];
      Object.keys(included).forEach((key) => {
        const agentId = Number(key);
        const relation = included[key][0], depth = included[key][1];
        if (frontier.indexOf(agentId) < 0 || depth >= maxDepth) return;
        const linked = direction === 'ancestor' ? (byId[agentId].parents || []) : (children[agentId] || []);
        linked.forEach((other) => {
          if (byId[other] == null || included[other] != null) return;
          included[other] = [direction, depth + 1];
          next.push(other);
        });
      });
      return next;
    }
    let frontier = [focus];
    while (frontier.length) frontier = addLayer(frontier, 'ancestor');
    frontier = [focus];
    while (frontier.length) frontier = addLayer(frontier, 'descendant');
    const omitted = {};
    function countBeyond(agentId, direction) {
      const linked = direction === 'ancestor' ? (byId[agentId].parents || []) : (children[agentId] || []);
      linked.forEach((other) => {
        if (byId[other] == null || included[other] != null || omitted[other]) return;
        omitted[other] = true;
        countBeyond(other, direction);
      });
    }
    Object.keys(included).forEach((key) => {
      const agentId = Number(key);
      const relation = included[key][0], depth = included[key][1];
      if (depth !== maxDepth) return;
      if (relation === 'self' || relation === 'ancestor') countBeyond(agentId, 'ancestor');
      if (relation === 'self' || relation === 'descendant') countBeyond(agentId, 'descendant');
    });
    const nodes = Object.keys(included).map((key) => {
      const agentId = Number(key);
      const row = byId[agentId];
      return {
        id: agentId, generation: row.generation, alive: row.alive, cause: row.cause,
        parents: row.parents, relation: included[key][0], depth: included[key][1],
      };
    });
    nodes.sort((a, b) => {
      const rank = (node) => node.relation === 'ancestor' ? 0 : node.relation === 'self' ? 1 : 2;
      return rank(a) - rank(b)
        || (a.relation === 'ancestor' ? b.depth - a.depth : a.depth - b.depth)
        || (a.id - b.id);
    });
    return { focus: focus, depth: maxDepth, omitted: Object.keys(omitted).length, nodes: nodes };
  }

  root.MaleCNSEco = {
    seasonAt, corpseFreshness, scavengeCorpses, compostCorpse, advancePatch,
    spawnHazards, competeHazard, resolveDeath, exchangeGifts, giftTotals,
    lifespanOf, familyTree,
    DEFAULTS: DEFAULTS,
    PRESETS: PRESETS,
    DECODER: DECODER,
    inheritGenome: inheritGenome,
    rulesFrom: rulesFrom,
    createWorld: createWorld,
    step: step,
    snapshot: snapshot,
    randomize: randomize,
  };
}(typeof window !== 'undefined' ? window : globalThis));
