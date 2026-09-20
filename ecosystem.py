"""Persistent multi-agent ecosystem. World rules are simulation abstractions."""
import json
import math
import random
from pathlib import Path
from sim import Circuit, integrate_motion, nearest_point, sensory_drives, validate_decoder, validate_graph

DEFAULTS = {
    'agents': 8,
    'patches': 6,
    'map_half': 20.0,
    'energy_start': 1.0,
    'energy_max': 2.0,
    'base_drain': 0.0012,
    'move_cost': 0.003,
    'meal': 0.55,
    'eat_radius': 0.4,
    'sense_range': 24.0,
    'max_age': 1200,
    'seed_ticks': 20,
    'grow_ticks': 70,
    'cooldown_ticks': 110,
    'corpse_ticks': 80,
    'max_population': 36,
    'mate_radius': 3.0,
    'min_repro_age': 80,
    'min_repro_energy': 1.15,
    'repro_cost': 0.4,
    'repro_cooldown': 90,
    'offspring_energy': 0.75,
    'food_rate': 1.0,
    'aging_rate': 1.0,
    'repro_rate': 1.0,
    'mutation_rate': 0.85,
    'mutation_sigma': 0.08,
}

INT_KEYS = ('agents', 'patches', 'max_age', 'seed_ticks', 'grow_ticks', 'cooldown_ticks',
            'corpse_ticks', 'max_population', 'min_repro_age', 'repro_cooldown')
RATE_KEYS = ('food_rate', 'aging_rate', 'repro_rate', 'mutation_rate', 'mutation_sigma')

# Relative body/decoder multipliers. Topology is not in the genome.
BASE_GENOME = {
    'turn_gain': 1.0,
    'sensory_gain': 1.0,
    'metabolism': 1.0,
    'speed': 1.0,
}
GENE_BOUNDS = {
    'turn_gain': (0.45, 2.0),
    'sensory_gain': (0.45, 2.0),
    'metabolism': (0.5, 1.8),
    'speed': (0.55, 1.75),
}


def _positive_number(name, value, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    if allow_zero:
        if value < 0:
            raise ValueError(f'{name} must be nonnegative')
    elif value <= 0:
        raise ValueError(f'{name} must be positive')
    return float(value)


def derived_lifecycle(food_rate, aging_rate, repro_rate):
    food_rate = _positive_number('food_rate', food_rate)
    aging_rate = _positive_number('aging_rate', aging_rate)
    repro_rate = _positive_number('repro_rate', repro_rate, allow_zero=True)
    return {
        'seed_ticks': max(4, int(round(DEFAULTS['seed_ticks'] / food_rate))),
        'grow_ticks': max(8, int(round(DEFAULTS['grow_ticks'] / food_rate))),
        'cooldown_ticks': max(12, int(round(DEFAULTS['cooldown_ticks'] / food_rate))),
        'max_age': max(80, int(round(DEFAULTS['max_age'] / aging_rate))),
        'repro_enabled': repro_rate > 0,
        'repro_cooldown': 10 ** 9 if repro_rate <= 0 else max(12, int(round(DEFAULTS['repro_cooldown'] / repro_rate))),
        'min_repro_energy': 99.0 if repro_rate <= 0 else max(0.55, DEFAULTS['min_repro_energy'] - 0.15 * (repro_rate - 1.0)),
        'mate_radius': DEFAULTS['mate_radius'] if repro_rate <= 0 else DEFAULTS['mate_radius'] * (0.75 + 0.25 * repro_rate),
    }


def rules_from(overrides):
    rules = dict(DEFAULTS)
    explicit = {key: value for key, value in overrides.items() if key in rules and value is not None}
    rules.update(explicit)
    derived = derived_lifecycle(rules['food_rate'], rules['aging_rate'], rules['repro_rate'])
    for key, value in derived.items():
        if key not in explicit:
            rules[key] = value
    for key in INT_KEYS:
        if type(rules[key]) is not int or rules[key] < 1:
            raise ValueError(f'{key} must be a positive integer')
    for key in RATE_KEYS:
        _positive_number(key, rules[key], allow_zero=(key in ('repro_rate', 'mutation_rate', 'mutation_sigma')))
    if rules['agents'] > 50:
        raise ValueError('agents must be 50 or fewer on the CPU path')
    if rules['max_population'] > 50:
        raise ValueError('max_population must be 50 or fewer on the CPU path')
    if rules['agents'] > rules['max_population']:
        raise ValueError('agents cannot exceed max_population')
    if rules['map_half'] < 4:
        raise ValueError('map_half must be at least 4')
    if not rules.get('repro_enabled', True):
        rules['repro_enabled'] = False
    return rules


def spawn_agents(count, radius, energy):
    agents = []
    for index in range(count):
        angle = 2 * math.pi * index / count
        agents.append({
            'id': index,
            'x': radius * math.cos(angle),
            'y': radius * math.sin(angle),
            'heading': angle + math.pi,
            'energy': energy,
            'age': 0,
            'alive': True,
            'meals': 0,
            'ate': False,
            'birth_tick': 0,
            'death_tick': None,
            'cause_of_death': None,
            'corpse_until': None,
            'last_repro': -10 ** 6,
            'generation': 0,
            'parents': None,
            'offspring': 0,
            'genome': dict(BASE_GENOME),
            'mutations': {},
        })
    return agents


def spawn_patches(count, radius, rng, rules):
    patches = []
    for index in range(count):
        angle = 2 * math.pi * index / count + rng.uniform(-0.15, 0.15)
        r = radius * rng.uniform(0.7, 1.0)
        mature = index % 2 == 0
        patches.append({
            'id': index,
            'x': r * math.cos(angle),
            'y': r * math.sin(angle),
            'stage': 'mature' if mature else 'growing',
            'timer': 0 if mature else rules['grow_ticks'] // 2,
            'nutrition': 1.0,
            'consumed_by': None,
        })
    return patches


def mature_locations(patches):
    return [(patch['x'], patch['y']) for patch in patches if patch['stage'] == 'mature']


def claim_patches(agents, patches, eat_radius):
    claimed = {}
    taken = set()
    for patch in patches:
        if patch['stage'] != 'mature':
            continue
        contenders = [agent for agent in agents
                      if agent['alive'] and agent['id'] not in taken
                      and math.hypot(agent['x'] - patch['x'], agent['y'] - patch['y']) < eat_radius]
        if not contenders:
            continue
        winner = min(contenders, key=lambda agent: agent['id'])
        claimed[patch['id']] = winner['id']
        taken.add(winner['id'])
    return claimed


def advance_patch(patch, rules):
    event = None
    if patch['stage'] == 'mature':
        return event
    patch['timer'] -= 1
    if patch['timer'] > 0:
        return event
    if patch['stage'] == 'cooldown':
        patch['stage'] = 'seed'
        patch['timer'] = rules['seed_ticks']
        patch['consumed_by'] = None
    elif patch['stage'] == 'seed':
        patch['stage'] = 'growing'
        patch['timer'] = rules['grow_ticks']
    elif patch['stage'] == 'growing':
        patch['stage'] = 'mature'
        patch['timer'] = 0
        event = 'food_mature'
    return event


def kill(agent, tick, cause, corpse_ticks):
    agent['alive'] = False
    agent['energy'] = 0.0
    agent['death_tick'] = tick
    agent['cause_of_death'] = cause
    agent['corpse_until'] = tick + corpse_ticks


def round_genome(genome):
    return {gene: round(float(genome[gene]), 4) for gene in BASE_GENOME}


def inherit_genome(mother, father, rng, rules):
    child = {}
    mutations = {}
    rate = rules.get('mutation_rate', DEFAULTS['mutation_rate'])
    sigma = rules.get('mutation_sigma', DEFAULTS['mutation_sigma'])
    for gene, (lo, hi) in GENE_BOUNDS.items():
        mid = 0.5 * (mother[gene] + father[gene])
        value = mid
        if rate > 0 and sigma > 0 and rng.random() < rate:
            value = max(lo, min(hi, mid * (1.0 + rng.gauss(0.0, sigma))))
        child[gene] = value
        if abs(value - mid) > 1e-6:
            mutations[gene] = round(value - mid, 4)
    return child, mutations


def decoder_for(base, genome):
    return {
        'turn_sign': base['turn_sign'],
        'turn_gain': base['turn_gain'] * genome['turn_gain'],
        'turn_clip': base['turn_clip'],
        'speed_gain': base['speed_gain'] * genome['speed'],
        'sensory_sign': base['sensory_sign'],
    }


def genome_stats(agents):
    living = [agent for agent in agents if agent['alive']]
    empty = {gene: 0.0 for gene in BASE_GENOME}
    if not living:
        return empty, empty
    means = {}
    stds = {}
    count = len(living)
    for gene in BASE_GENOME:
        values = [agent['genome'][gene] for agent in living]
        mean = sum(values) / count
        variance = sum((value - mean) ** 2 for value in values) / count
        means[gene] = round(mean, 4)
        stds[gene] = round(variance ** 0.5, 4)
    return means, stds


def can_reproduce(agent, tick, rules):
    return (rules.get('repro_enabled', True)
            and agent['alive']
            and agent['age'] >= rules['min_repro_age']
            and agent['energy'] >= rules['min_repro_energy']
            and (tick - agent['last_repro']) >= rules['repro_cooldown'])


def reproduce(agents, circuits, graph, tick, rules, rng, events, disconnected, shuffle_seed):
    if not rules.get('repro_enabled', True):
        return 0
    candidates = [agent for agent in agents if can_reproduce(agent, tick, rules)]
    candidates.sort(key=lambda agent: agent['id'])
    used = set()
    births = 0
    for parent in candidates:
        if parent['id'] in used:
            continue
        partner = None
        best = rules['mate_radius']
        for other in candidates:
            if other['id'] <= parent['id'] or other['id'] in used:
                continue
            distance = math.hypot(parent['x'] - other['x'], parent['y'] - other['y'])
            if distance < best:
                best = distance
                partner = other
        if partner is None:
            continue
        if sum(agent['alive'] for agent in agents) >= rules['max_population']:
            events.append({'tick': tick, 'kind': 'repro_capped',
                           'text': f'population cap {rules["max_population"]} blocked a birth'})
            break
        used.add(parent['id'])
        used.add(partner['id'])
        parent['energy'] -= rules['repro_cost']
        partner['energy'] -= rules['repro_cost']
        parent['last_repro'] = tick
        partner['last_repro'] = tick
        parent['offspring'] += 1
        partner['offspring'] += 1
        angle = rng.random() * 2 * math.pi
        half = rules['map_half']
        x = max(-half, min(half, (parent['x'] + partner['x']) / 2 + 0.35 * math.cos(angle)))
        y = max(-half, min(half, (parent['y'] + partner['y']) / 2 + 0.35 * math.sin(angle)))
        child_id = max(agent['id'] for agent in agents) + 1
        genome, mutations = inherit_genome(parent['genome'], partner['genome'], rng, rules)
        agents.append({
            'id': child_id,
            'x': x,
            'y': y,
            'heading': angle,
            'energy': rules['offspring_energy'],
            'age': 0,
            'alive': True,
            'meals': 0,
            'ate': False,
            'birth_tick': tick,
            'death_tick': None,
            'cause_of_death': None,
            'corpse_until': None,
            'last_repro': tick,
            'generation': max(parent['generation'], partner['generation']) + 1,
            'parents': (parent['id'], partner['id']),
            'offspring': 0,
            'genome': genome,
            'mutations': mutations,
        })
        circuits.append(Circuit(graph, disconnected=disconnected, shuffle_seed=shuffle_seed))
        mutated = ', '.join(f'{gene} {genome[gene]:.2f}' for gene in mutations) if mutations else 'no mutation'
        events.append({
            'tick': tick,
            'kind': 'born',
            'agent': child_id,
            'parents': [parent['id'], partner['id']],
            'mutations': mutations,
            'text': f'F{child_id} born to F{parent["id"]} and F{partner["id"]} · {mutated}',
        })
        births += 1
    return births


def snapshot_agent(agent, left, right, speed):
    parents = agent['parents']
    return {
        'id': agent['id'],
        'x': round(agent['x'], 6),
        'y': round(agent['y'], 6),
        'heading': round(agent['heading'], 6),
        'energy': round(max(0.0, agent['energy']), 6),
        'age': agent['age'],
        'alive': agent['alive'],
        'meals': agent['meals'],
        'ate': agent['ate'],
        'cause_of_death': agent['cause_of_death'],
        'corpse': bool(agent['corpse_until'] is not None),
        'generation': agent['generation'],
        'parents': list(parents) if parents else None,
        'offspring': agent['offspring'],
        'genome': round_genome(agent['genome']),
        'mutations': dict(agent.get('mutations') or {}),
        'left_motor': round(left, 6),
        'right_motor': round(right, 6),
        'speed': round(speed, 6),
    }


def snapshot_patch(patch):
    return {
        'id': patch['id'],
        'x': round(patch['x'], 6),
        'y': round(patch['y'], 6),
        'stage': patch['stage'],
    }


def motors_for(agents, circuits, edible, decoder, rules, drive_enabled):
    motors = []
    for agent, circuit in zip(agents, circuits):
        agent['ate'] = False
        speed = 0.0
        if not agent['alive']:
            motors.append((0.0, 0.0, speed))
            continue
        agent['age'] += 1
        target, distance = nearest_point(agent['x'], agent['y'], edible)
        bearing = 0.0
        stimulus = 0.0
        if target is not None and drive_enabled:
            bearing = math.atan2(target[1] - agent['y'], target[0] - agent['x']) - agent['heading']
            bearing = math.atan2(math.sin(bearing), math.cos(bearing))
            stimulus = max(0.0, 1.0 - distance / rules['sense_range']) * agent['genome']['sensory_gain']
        body = decoder_for(decoder, agent['genome'])
        circuit.step(sensory_drives(circuit.nodes, body, bearing, stimulus))
        left, right = circuit.motors()
        agent['x'], agent['y'], agent['heading'], speed = integrate_motion(
            body, agent['x'], agent['y'], agent['heading'], left, right)
        motors.append((left, right, speed))
    return motors


def simulate_ecosystem(path, ticks, seed, *, drive_enabled=True, disconnected=False, shuffle_seed=None,
                       turn_sign=1, turn_gain=0.15, turn_clip=0.3, speed_gain=0.13, sensory_sign=1, **overrides):
    if type(ticks) is not int or ticks < 1:
        raise ValueError('ticks must be a positive integer')
    rules = rules_from(overrides)
    decoder = validate_decoder(turn_sign, turn_gain, turn_clip, speed_gain, sensory_sign)
    graph = json.loads(Path(path).read_text())
    validate_graph(graph)
    rng = random.Random(seed)
    agents = spawn_agents(rules['agents'], rules['map_half'] * 0.85, rules['energy_start'])
    patches = spawn_patches(rules['patches'], rules['map_half'] * 0.4, rng, rules)
    circuits = [Circuit(graph, disconnected=disconnected, shuffle_seed=shuffle_seed) for _ in agents]
    events = []
    history = []
    births = 0
    peak = rules['agents']
    for tick in range(ticks):
        motors = motors_for(agents, circuits, mature_locations(patches), decoder, rules, drive_enabled)
        claimed = claim_patches(agents, patches, rules['eat_radius'])
        for patch in patches:
            if patch['id'] in claimed:
                eater = next(agent for agent in agents if agent['id'] == claimed[patch['id']])
                eater['ate'] = True
                eater['meals'] += 1
                eater['energy'] = min(rules['energy_max'], eater['energy'] + rules['meal'] * patch['nutrition'])
                patch['stage'] = 'cooldown'
                patch['timer'] = rules['cooldown_ticks']
                patch['consumed_by'] = eater['id']
                events.append({'tick': tick, 'kind': 'ate', 'agent': eater['id'], 'patch': patch['id'],
                               'text': f'F{eater["id"]} ate patch {patch["id"]}'})
            else:
                matured = advance_patch(patch, rules)
                if matured:
                    events.append({'tick': tick, 'kind': 'food_mature', 'patch': patch['id'],
                                   'text': f'patch {patch["id"]} matured'})
        births += reproduce(agents, circuits, graph, tick, rules, rng, events, disconnected, shuffle_seed)
        while len(motors) < len(agents):
            motors.append((0.0, 0.0, 0.0))
        for agent, (left, right, speed) in zip(agents, motors):
            if not agent['alive']:
                continue
            agent['energy'] -= rules['base_drain'] * agent['genome']['metabolism'] + rules['move_cost'] * speed
            if agent['age'] >= rules['max_age']:
                kill(agent, tick, 'old_age', rules['corpse_ticks'])
                events.append({'tick': tick, 'kind': 'died', 'agent': agent['id'], 'cause': 'old_age',
                               'text': f'F{agent["id"]} died of old age'})
            elif agent['energy'] <= 0:
                kill(agent, tick, 'starvation', rules['corpse_ticks'])
                events.append({'tick': tick, 'kind': 'died', 'agent': agent['id'], 'cause': 'starvation',
                               'text': f'F{agent["id"]} starved'})
        corpses = []
        for agent in agents:
            if agent['corpse_until'] is None:
                continue
            if tick >= agent['corpse_until']:
                events.append({'tick': tick, 'kind': 'corpse_decayed', 'agent': agent['id'],
                               'text': f'F{agent["id"]} corpse decayed'})
                agent['corpse_until'] = None
            else:
                corpses.append({'id': agent['id'], 'x': round(agent['x'], 6), 'y': round(agent['y'], 6),
                                'cause': agent['cause_of_death']})
        alive = [agent for agent in agents if agent['alive']]
        peak = max(peak, len(alive))
        means, stds = genome_stats(agents)
        history.append({
            'tick': tick,
            'agents': [snapshot_agent(agent, left, right, speed)
                       for agent, (left, right, speed) in zip(agents, motors)],
            'patches': [snapshot_patch(patch) for patch in patches],
            'corpses': corpses,
            'alive': len(alive),
            'born': births,
            'mature_food': sum(patch['stage'] == 'mature' for patch in patches),
            'mean_energy': round(sum(agent['energy'] for agent in alive) / len(alive), 6) if alive else 0.0,
            'mean_speed': means['speed'],
            'mean_metabolism': means['metabolism'],
            'genome_mean': means,
            'genome_std': stds,
        })
    return {
        'mode': 'ecosystem',
        'rules': rules,
        'events': events,
        'final': {
            'alive': sum(agent['alive'] for agent in agents),
            'starved': sum(agent['cause_of_death'] == 'starvation' for agent in agents),
            'old_age': sum(agent['cause_of_death'] == 'old_age' for agent in agents),
            'meals': sum(agent['meals'] for agent in agents),
            'births': births,
            'peak': peak,
            'generation': max((agent['generation'] for agent in agents), default=0),
            'genome_mean': genome_stats(agents)[0],
            'genome_std': genome_stats(agents)[1],
        },
        'ticks': history,
    }


def summarize_ecosystem(result):
    final = result['final']
    rules = result['rules']
    last = result['ticks'][-1]
    means = final.get('genome_mean') or {}
    return (f"ecosystem {rules['agents']} start, {rules['patches']} patches, {len(result['ticks'])} ticks; "
            f"alive {final['alive']}, births {final['births']}, gen {final['generation']}, "
            f"starved {final['starved']}, old_age {final['old_age']}, "
            f"meals {final['meals']}, mature food {last['mature_food']}, "
            f"mean speed {means.get('speed', 1):.2f}, metabolism {means.get('metabolism', 1):.2f}")
