"""Scarce-food survival contest. Same toy controller, independent agent state."""
import json
import math
import random
from pathlib import Path
from sim import Circuit, integrate_motion, nearest_point, sensory_drives, validate_decoder, validate_graph

ENERGY_START = 1.0
ENERGY_DRAIN = 0.002
ENERGY_MEAL = 1.0
EAT_RADIUS = 0.4
SENSE_RANGE = 24.0
DEFAULT_AGENTS = 10
DEFAULT_FOODS = 3
DEFAULT_MAP = 20.0


def validate_contest(agents, foods, map_half, ticks):
    for name, value in [('agents', agents), ('foods', foods), ('ticks', ticks)]:
        if type(value) is not int or value < 1:
            raise ValueError(f'{name} must be a positive integer')
    if agents > 50:
        raise ValueError('agents must be 50 or fewer on the CPU path')
    if isinstance(map_half, bool) or not isinstance(map_half, (int, float)) or not math.isfinite(map_half) or map_half < 4:
        raise ValueError('map_half must be a finite value of at least 4')
    return int(agents), int(foods), float(map_half)


def spawn_agents(count, radius):
    agents = []
    for index in range(count):
        angle = 2 * math.pi * index / count
        agents.append({
            'id': index,
            'x': radius * math.cos(angle),
            'y': radius * math.sin(angle),
            'heading': angle + math.pi,
            'energy': ENERGY_START,
            'alive': True,
            'meals': 0,
            'ate': False,
            'death_tick': None,
        })
    return agents


def spawn_foods(count, radius, rng):
    foods = []
    inner = max(2.0, radius * 0.25)
    for _ in range(count * 40):
        if len(foods) >= count:
            break
        angle = rng.uniform(-math.pi, math.pi)
        r = rng.uniform(inner, radius)
        point = (r * math.cos(angle), r * math.sin(angle))
        if all(math.hypot(point[0] - other[0], point[1] - other[1]) >= 3.0 for other in foods):
            foods.append(point)
    if len(foods) < count:
        raise ValueError('Could not place scarce food without overlap')
    return foods


def contest_rank(agent):
    lived = agent['death_tick'] if agent['death_tick'] is not None else 10 ** 9
    return (agent['alive'], agent['meals'], agent['energy'], lived, -agent['id'])


def claim_meals(agents, foods):
    """Lowest living id wins a pellet if several arrive together. One meal per fly per tick."""
    claimed = {}
    taken_agents = set()
    for food_index, food in enumerate(foods):
        contenders = [agent for agent in agents
                      if agent['alive'] and agent['id'] not in taken_agents
                      and math.hypot(agent['x'] - food[0], agent['y'] - food[1]) < EAT_RADIUS]
        if not contenders:
            continue
        winner = min(contenders, key=lambda agent: agent['id'])
        claimed[food_index] = winner['id']
        taken_agents.add(winner['id'])
    return claimed


def snapshot_agent(agent, left, right, activity):
    return {
        'id': agent['id'],
        'x': round(agent['x'], 6),
        'y': round(agent['y'], 6),
        'heading': round(agent['heading'], 6),
        'energy': round(agent['energy'], 6),
        'alive': agent['alive'],
        'meals': agent['meals'],
        'ate': agent['ate'],
        'left_motor': round(left, 6),
        'right_motor': round(right, 6),
        'mean_activity': round(sum(activity) / len(activity), 6) if activity else 0.0,
    }


def simulate_contest(path, ticks, seed, *, agents=DEFAULT_AGENTS, foods=DEFAULT_FOODS, map_half=DEFAULT_MAP,
                     drive_enabled=True, disconnected=False, shuffle_seed=None,
                     turn_sign=1, turn_gain=0.15, turn_clip=0.3, speed_gain=0.13, sensory_sign=1):
    agents, foods, map_half = validate_contest(agents, foods, map_half, ticks)
    decoder = validate_decoder(turn_sign, turn_gain, turn_clip, speed_gain, sensory_sign)
    graph = json.loads(Path(path).read_text())
    validate_graph(graph)
    rng = random.Random(seed)
    ring = map_half * 0.85
    state = spawn_agents(agents, ring)
    pellets = spawn_foods(foods, map_half * 0.45, rng)
    circuits = [Circuit(graph, disconnected=disconnected, shuffle_seed=shuffle_seed) for _ in state]
    history = []
    for tick in range(ticks):
        motors = []
        for agent, circuit in zip(state, circuits):
            agent['ate'] = False
            if not agent['alive']:
                motors.append((0.0, 0.0, list(circuit.activity)))
                continue
            target, distance = nearest_point(agent['x'], agent['y'], pellets)
            bearing = 0.0
            stimulus = 0.0
            if target is not None and drive_enabled:
                bearing = math.atan2(target[1] - agent['y'], target[0] - agent['x']) - agent['heading']
                bearing = math.atan2(math.sin(bearing), math.cos(bearing))
                stimulus = max(0.0, 1.0 - distance / SENSE_RANGE)
            activity = circuit.step(sensory_drives(circuit.nodes, decoder, bearing, stimulus))
            left, right = circuit.motors()
            agent['x'], agent['y'], agent['heading'], _speed = integrate_motion(
                decoder, agent['x'], agent['y'], agent['heading'], left, right)
            motors.append((left, right, activity))
        claimed = claim_meals(state, pellets)
        remaining = []
        eaten_ids = set(claimed.values())
        for food_index, food in enumerate(pellets):
            if food_index in claimed:
                continue
            remaining.append(food)
        pellets = remaining
        for agent, (left, right, activity) in zip(state, motors):
            if agent['id'] in eaten_ids:
                agent['ate'] = True
                agent['meals'] += 1
                agent['energy'] = min(2.0, agent['energy'] + ENERGY_MEAL)
            if agent['alive']:
                agent['energy'] -= ENERGY_DRAIN
                if agent['energy'] <= 0:
                    agent['energy'] = 0.0
                    agent['alive'] = False
                    agent['death_tick'] = tick
        history.append({
            'tick': tick,
            'foods': [{'x': round(x, 6), 'y': round(y, 6)} for x, y in pellets],
            'agents': [snapshot_agent(agent, left, right, activity)
                       for agent, (left, right, activity) in zip(state, motors)],
        })
    ranking = sorted(state, key=contest_rank, reverse=True)
    winner = ranking[0]
    return {
        'mode': 'contest',
        'rules': {
            'agents': agents,
            'foods': foods,
            'map_half': map_half,
            'energy_start': ENERGY_START,
            'energy_drain': ENERGY_DRAIN,
            'energy_meal': ENERGY_MEAL,
            'eat_radius': EAT_RADIUS,
            'sense_range': SENSE_RANGE,
            'respawn': False,
        },
        'ranking': [{'id': agent['id'], 'meals': agent['meals'], 'energy': round(agent['energy'], 6),
                     'alive': agent['alive'], 'death_tick': agent['death_tick']} for agent in ranking],
        'winner': {'id': winner['id'], 'meals': winner['meals'], 'energy': round(winner['energy'], 6),
                   'alive': winner['alive']},
        'ticks': history,
    }


def summarize_contest(result):
    winner = result['winner']
    status = 'alive' if winner['alive'] else 'dead'
    lines = [f"{result['rules']['agents']} flies, {result['rules']['foods']} pellets, "
             f"map ±{result['rules']['map_half']:g}; winner fly {winner['id']} "
             f"({winner['meals']} meals, energy {winner['energy']:.3f}, {status})"]
    for place, agent in enumerate(result['ranking'], start=1):
        state = 'alive' if agent['alive'] else f"died@{agent['death_tick']}"
        lines.append(f"  {place}. F{agent['id']}  meals={agent['meals']}  energy={agent['energy']:.3f}  {state}")
    return '\n'.join(lines)
