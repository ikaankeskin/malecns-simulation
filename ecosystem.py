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
}


def rules_from(overrides):
    rules = dict(DEFAULTS)
    for key, value in overrides.items():
        if key in rules and value is not None:
            rules[key] = value
    for key in ['agents', 'patches', 'max_age', 'seed_ticks', 'grow_ticks', 'cooldown_ticks', 'corpse_ticks']:
        if type(rules[key]) is not int or rules[key] < 1:
            raise ValueError(f'{key} must be a positive integer')
    if rules['agents'] > 50:
        raise ValueError('agents must be 50 or fewer on the CPU path')
    if rules['map_half'] < 4:
        raise ValueError('map_half must be at least 4')
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


def snapshot_agent(agent, left, right, speed):
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
    for tick in range(ticks):
        motors = []
        edible = mature_locations(patches)
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
                stimulus = max(0.0, 1.0 - distance / rules['sense_range'])
            circuit.step(sensory_drives(circuit.nodes, decoder, bearing, stimulus))
            left, right = circuit.motors()
            agent['x'], agent['y'], agent['heading'], speed = integrate_motion(
                decoder, agent['x'], agent['y'], agent['heading'], left, right)
            motors.append((left, right, speed))
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
        for agent, (left, right, speed) in zip(agents, motors):
            if not agent['alive']:
                continue
            agent['energy'] -= rules['base_drain'] + rules['move_cost'] * speed
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
        history.append({
            'tick': tick,
            'agents': [snapshot_agent(agent, left, right, speed)
                       for agent, (left, right, speed) in zip(agents, motors)],
            'patches': [snapshot_patch(patch) for patch in patches],
            'corpses': corpses,
            'alive': len(alive),
            'mature_food': sum(patch['stage'] == 'mature' for patch in patches),
            'mean_energy': round(sum(agent['energy'] for agent in alive) / len(alive), 6) if alive else 0.0,
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
        },
        'ticks': history,
    }


def summarize_ecosystem(result):
    final = result['final']
    rules = result['rules']
    last = result['ticks'][-1]
    return (f"ecosystem {rules['agents']} flies, {rules['patches']} patches, {len(result['ticks'])} ticks; "
            f"alive {final['alive']}, starved {final['starved']}, old_age {final['old_age']}, "
            f"meals {final['meals']}, mature food {last['mature_food']}")
