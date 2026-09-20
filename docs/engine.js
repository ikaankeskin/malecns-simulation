/* Live ecosystem engine. Dynamics are simulation abstractions; DNg13 topology is MaleCNS-derived. */
(function (root) {
  const DEFAULTS = {
    agents: 8,
    patches: 6,
    map_half: 20,
    energy_start: 1,
    energy_max: 2,
    base_drain: 0.0012,
    move_cost: 0.003,
    meal: 0.55,
    eat_radius: 0.4,
    sense_range: 24,
    max_age: 1200,
    seed_ticks: 20,
    grow_ticks: 70,
    cooldown_ticks: 110,
    corpse_ticks: 80,
    max_population: 36,
    mate_radius: 3,
    min_repro_age: 80,
    min_repro_energy: 1.15,
    repro_cost: 0.4,
    repro_cooldown: 90,
    offspring_energy: 0.75,
    food_rate: 1,
    aging_rate: 1,
    repro_rate: 1,
    mutation_rate: 0.85,
    mutation_sigma: 0.08,
  };

  const BASE_GENOME = { turn_gain: 1, sensory_gain: 1, metabolism: 1, speed: 1 };
  const GENE_BOUNDS = {
    turn_gain: [0.45, 2],
    sensory_gain: [0.45, 2],
    metabolism: [0.5, 1.8],
    speed: [0.55, 1.75],
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
        value = clamp(mid * (1 + gauss(random, sigma)), bounds[0], bounds[1]);
      }
      child[gene] = value;
      if (Math.abs(value - mid) > 1e-6) mutations[gene] = value - mid;
    });
    return [child, mutations];
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
    const food = Math.max(0.2, Number(ui.food_rate) || 1);
    const aging = Math.max(0.2, Number(ui.aging_rate) || 1);
    const repro = Math.max(0, Number(ui.repro_rate) || 0);
    const agents = clamp(Math.round(Number(ui.agents) || 8), 2, 24);
    const patches = clamp(Math.round(Number(ui.patches) || 6), 2, 12);
    return Object.assign({}, DEFAULTS, {
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
      max_population: clamp(Math.round(Number(ui.max_population) || 36), agents, 40),
      mutation_rate: clamp(Number(ui.mutation_rate == null ? DEFAULTS.mutation_rate : ui.mutation_rate), 0, 1),
      mutation_sigma: Math.max(0, Number(ui.mutation_sigma == null ? DEFAULTS.mutation_sigma : ui.mutation_sigma)),
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
      });
    }
    return agents;
  }

  function spawnPatches(count, radius, random, rules) {
    const patches = [];
    for (let i = 0; i < count; i += 1) {
      const angle = 2 * Math.PI * i / count + (random() * 0.3 - 0.15);
      const r = radius * (0.7 + random() * 0.3);
      const mature = i % 2 === 0;
      patches.push({
        id: i, x: r * Math.cos(angle), y: r * Math.sin(angle),
        stage: mature ? 'mature' : 'growing',
        timer: mature ? 0 : Math.floor(rules.grow_ticks / 2),
        nutrition: 1, consumed_by: null,
      });
    }
    return patches;
  }

  function advancePatch(patch, rules) {
    if (patch.stage === 'mature') return null;
    patch.timer -= 1;
    if (patch.timer > 0) return null;
    if (patch.stage === 'cooldown') {
      patch.stage = 'seed';
      patch.timer = rules.seed_ticks;
      patch.consumed_by = null;
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
      circuits: [],
      events: [],
      births: 0,
      peak: rules.agents,
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
      const angle = world.random() * 2 * Math.PI;
      const half = rules.map_half;
      const inherited = inheritGenome(parent.genome, partner.genome, world.random, rules);
      const child = {
        id: world.agents.reduce((max, agent) => Math.max(max, agent.id), 0) + 1,
        x: clamp((parent.x + partner.x) / 2 + 0.35 * Math.cos(angle), -half, half),
        y: clamp((parent.y + partner.y) / 2 + 0.35 * Math.sin(angle), -half, half),
        heading: angle, energy: rules.offspring_energy, age: 0, alive: true, meals: 0, ate: false,
        birth_tick: tick, death_tick: null, cause_of_death: null, corpse_until: null,
        last_repro: tick, generation: Math.max(parent.generation, partner.generation) + 1,
        parents: [parent.id, partner.id], offspring: 0, left: 0, right: 0, speed: 0, trail: [],
        genome: inherited[0], mutations: inherited[1],
      };
      world.agents.push(child);
      world.circuits.push(new Circuit(world.graph));
      world.births += 1;
      const mutated = Object.keys(inherited[1]);
      world.events.push({
        tick: tick, kind: 'born', agent: child.id, parents: child.parents, mutations: inherited[1],
        text: 'F' + child.id + ' born to F' + parent.id + ' and F' + partner.id + ' · ' +
          (mutated.length ? mutated.map((gene) => gene + ' ' + child.genome[gene].toFixed(2)).join(', ') : 'no mutation'),
      });
    }
  }

  function step(world) {
    const rules = world.rules;
    const decoder = world.decoder;
    const edible = world.patches.filter((patch) => patch.stage === 'mature').map((patch) => [patch.x, patch.y]);
    world.agents.forEach((agent, index) => {
      agent.ate = false;
      agent.speed = 0;
      if (!agent.alive) { agent.left = 0; agent.right = 0; return; }
      agent.age += 1;
      const found = nearest(agent.x, agent.y, edible);
      let bearing = 0;
      let stimulus = 0;
      if (found[0]) {
        bearing = Math.atan2(found[0][1] - agent.y, found[0][0] - agent.x) - agent.heading;
        bearing = Math.atan2(Math.sin(bearing), Math.cos(bearing));
        stimulus = Math.max(0, 1 - found[1] / rules.sense_range) * agent.genome.sensory_gain;
      }
      const circuit = world.circuits[index];
      const body = decoderFor(decoder, agent.genome);
      circuit.step(sensoryDrives(circuit.nodes, body, bearing, stimulus));
      const motors = circuit.motors();
      const moved = integrateMotion(body, agent.x, agent.y, agent.heading, motors[0], motors[1]);
      agent.x = moved[0]; agent.y = moved[1]; agent.heading = moved[2]; agent.speed = moved[3];
      agent.left = motors[0]; agent.right = motors[1];
      agent.trail.push([agent.x, agent.y]);
      if (agent.trail.length > 90) agent.trail.shift();
    });
    const taken = {};
    world.patches.forEach((patch) => {
      if (patch.stage !== 'mature') {
        if (advancePatch(patch, rules) === 'food_mature') {
          world.events.push({ tick: world.tick, kind: 'food_mature', text: 'patch ' + patch.id + ' matured' });
        }
        return;
      }
      const contenders = world.agents.filter((agent) => agent.alive && !taken[agent.id]
        && Math.hypot(agent.x - patch.x, agent.y - patch.y) < rules.eat_radius);
      if (!contenders.length) return;
      const winner = contenders.reduce((best, agent) => agent.id < best.id ? agent : best);
      taken[winner.id] = true;
      winner.ate = true;
      winner.meals += 1;
      winner.energy = Math.min(rules.energy_max, winner.energy + rules.meal * patch.nutrition);
      patch.stage = 'cooldown';
      patch.timer = rules.cooldown_ticks;
      patch.consumed_by = winner.id;
      world.events.push({ tick: world.tick, kind: 'ate', text: 'F' + winner.id + ' ate patch ' + patch.id });
    });
    reproduce(world);
    world.agents.forEach((agent) => {
      if (!agent.alive) return;
      agent.energy -= rules.base_drain * agent.genome.metabolism + rules.move_cost * agent.speed;
      if (agent.age >= rules.max_age) {
        kill(agent, world.tick, 'old_age', rules.corpse_ticks);
        world.events.push({ tick: world.tick, kind: 'died', text: 'F' + agent.id + ' died of old age' });
      } else if (agent.energy <= 0) {
        kill(agent, world.tick, 'starvation', rules.corpse_ticks);
        world.events.push({ tick: world.tick, kind: 'died', text: 'F' + agent.id + ' starved' });
      }
    });
    world.agents.forEach((agent) => {
      if (agent.corpse_until != null && world.tick >= agent.corpse_until) {
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
      corpses: world.agents.filter((agent) => !agent.alive && agent.corpse_until != null),
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

  root.MaleCNSEco = {
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
