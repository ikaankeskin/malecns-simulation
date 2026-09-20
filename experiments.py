"""Decoder mapping experiment for the exploratory rate model.

Signs and gains are interface parameters. A mapping that collects food is not
evidence that the biological circuit encodes foraging.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
from sim import Circuit, simulate, validate_decoder


SATURATION_LIMIT = 0.25
TURN_GAINS = (0.15, 0.5, 1.0)
BASELINE_DECODER = {'name': 'sensory+1_turn+1_gain0.15', 'turn_sign': 1, 'turn_gain': 0.15, 'sensory_sign': 1}


def probe(graph, side):
    c = Circuit(graph)
    drives = [0.5 if n['role'] == 'sensory' and (side == 'both' or n['side'] == side) else 0.0 for n in c.nodes]
    for _ in range(200):
        c.step(drives)
    left, right = c.motors()
    return {'left_motor': left, 'right_motor': right, 'right_minus_left': right - left,
            'saturated_neurons': sum(a >= .999 for a in c.activity)}


def candidate_decoders():
    return [{'name': f'sensory{sensory_sign:+d}_turn{turn_sign:+d}_gain{turn_gain:.2f}',
             'turn_sign': turn_sign, 'turn_gain': turn_gain, 'sensory_sign': sensory_sign}
            for sensory_sign in (1, -1) for turn_sign in (1, -1) for turn_gain in TURN_GAINS]


def decoder_kwargs(decoder):
    return validate_decoder(turn_sign=decoder['turn_sign'], turn_gain=decoder['turn_gain'],
                            sensory_sign=decoder['sensory_sign'])


def food_at(seed, radius=6.0):
    angle = random.Random(seed).uniform(-math.pi, math.pi)
    return (radius * math.cos(angle), radius * math.sin(angle))


def min_distance_to_first_food(trace, initial_food):
    nearest = math.hypot(initial_food[0], initial_food[1])
    for tick in trace:
        nearest = min(nearest, math.hypot(initial_food[0] - tick['x'], initial_food[1] - tick['y']))
        if tick['ate']:
            break
    return nearest


def summarize_trace(trace, initial_food):
    points = [(0.0, 0.0)] + [(tick['x'], tick['y']) for tick in trace]
    return {
        'food_collected': sum(tick['ate'] for tick in trace),
        'distance_travelled': sum(math.dist(a, b) for a, b in zip(points, points[1:])),
        'mean_motor_activity': statistics.mean(tick['left_motor'] + tick['right_motor'] for tick in trace),
        'mean_saturated_fraction': statistics.mean(tick['saturated_fraction'] for tick in trace),
        'min_distance_to_first_food': min_distance_to_first_food(trace, initial_food),
    }


def run_trial(path, ticks, seed, decoder, **sim_kwargs):
    initial_food = food_at(seed)
    trace = simulate(path, ticks, seed, initial_food=initial_food, **decoder_kwargs(decoder), **sim_kwargs)
    summary = summarize_trace(trace, initial_food)
    summary['seed'] = seed
    summary['initial_food'] = initial_food
    return summary


def aggregate(runs, extra=None):
    summary = {
        'mean_food_collected': statistics.mean(run['food_collected'] for run in runs),
        'mean_distance_travelled': statistics.mean(run['distance_travelled'] for run in runs),
        'mean_min_distance_to_first_food': statistics.mean(run['min_distance_to_first_food'] for run in runs),
        'mean_motor_activity': statistics.mean(run['mean_motor_activity'] for run in runs),
        'mean_saturated_fraction': statistics.mean(run['mean_saturated_fraction'] for run in runs),
        'runs': runs,
    }
    if extra:
        summary.update(extra)
    return summary


def selection_key(summary):
    return (summary['mean_food_collected'], -summary['mean_min_distance_to_first_food'],
            -summary['mean_saturated_fraction'], summary['decoder']['name'])


def select_decoder(sweep):
    eligible = [item for item in sweep if item['mean_saturated_fraction'] <= SATURATION_LIMIT]
    pool = eligible or sweep
    selected = max(pool, key=selection_key)
    return {
        'decoder': selected['decoder'],
        'development_food_collected': selected['mean_food_collected'],
        'development_min_distance': selected['mean_min_distance_to_first_food'],
        'eligible': bool(eligible),
        'saturation_limit': SATURATION_LIMIT,
        'rule': 'Among candidates with mean saturation <= 0.25, maximize mean food, then minimize mean closest approach to the first pellet. Name is the deterministic tie-break.',
    }


def evaluate_condition(path, ticks, seeds, decoder, **sim_kwargs):
    return aggregate([run_trial(path, ticks, seed, decoder, **sim_kwargs) for seed in seeds],
                     extra={'decoder': {k: decoder[k] for k in ('name', 'turn_sign', 'turn_gain', 'sensory_sign')}})


def decoder_experiment(path, ticks=500, development_seeds=10, held_out_seeds=10):
    if ticks < 1 or development_seeds < 1 or held_out_seeds < 1:
        raise ValueError('ticks and seed counts must be positive')
    path = Path(path)
    graph = json.loads(path.read_text())
    dev_ids = list(range(development_seeds))
    hold_ids = list(range(development_seeds, development_seeds + held_out_seeds))
    sweep = []
    for decoder in candidate_decoders():
        item = evaluate_condition(path, ticks, dev_ids, decoder)
        sweep.append(item)
    selection = select_decoder(sweep)
    selected = selection['decoder']
    selected_meta = {k: selected[k] for k in ('name', 'turn_sign', 'turn_gain', 'sensory_sign')}
    held_out = {
        'intact_baseline': evaluate_condition(path, ticks, hold_ids, BASELINE_DECODER),
        'intact_selected': evaluate_condition(path, ticks, hold_ids, selected),
        'shuffled_selected': aggregate(
            [run_trial(path, ticks, seed, selected, shuffle_seed=seed) for seed in hold_ids],
            extra={'decoder': selected_meta},
        ),
        'disconnected_selected': evaluate_condition(path, ticks, hold_ids, selected, disconnected=True),
        'no_input_selected': evaluate_condition(path, ticks, hold_ids, selected, drive_enabled=False),
    }
    return {
        'graph_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'nodes': len(graph['nodes']),
        'connections': len(graph['edges']),
        'retained_synapses': sum(edge['weight'] for edge in graph['edges']),
        'ticks_per_run': ticks,
        'development_seeds': dev_ids,
        'held_out_seeds': hold_ids,
        'controller': {
            'model': 'bounded rate model',
            'sign_policy': 'all excitatory (assumption)',
            'edge_gain': 'raw synapse count / 100',
            'update': 'clip(0.75*old + 0.25*(input + recurrent), 0, 1)',
            'movement': 'speed = 0.13*min(1,L+R); turn = clip(turn_sign*turn_gain*(R-L), -0.3, 0.3)',
            'sensory': 'drive = stimulus * (1 + sensory_sign * side * sin(bearing))',
            'learning': False,
        },
        'static_probes': {side: probe(graph, side) for side in ['left', 'right', 'both', 'none']},
        'development_sweep': sweep,
        'selection': selection,
        'held_out': held_out,
    }


def evaluate(path, ticks=500, seeds=10):
    """Intact-vs-control battery with the baseline decoder."""
    if ticks < 1 or seeds < 1:
        raise ValueError('ticks and seeds must be positive')
    path = Path(path)
    graph = json.loads(path.read_text())
    seed_ids = list(range(seeds))
    return {
        'graph_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'nodes': len(graph['nodes']),
        'connections': len(graph['edges']),
        'retained_synapses': sum(edge['weight'] for edge in graph['edges']),
        'ticks_per_run': ticks,
        'seed_count': seeds,
        'controller': {
            'model': 'bounded rate model',
            'sign_policy': 'all excitatory (assumption)',
            'edge_gain': 'raw synapse count / 100',
            'update': 'clip(0.75*old + 0.25*(input + recurrent), 0, 1)',
            'movement': 'speed = 0.13*min(1,L+R); turn = clip(turn_sign*turn_gain*(R-L), -0.3, 0.3)',
            'learning': False,
        },
        'static_probes': {side: probe(graph, side) for side in ['left', 'right', 'both', 'none']},
        'controls': {
            'intact': evaluate_condition(path, ticks, seed_ids, BASELINE_DECODER),
            'disconnected': evaluate_condition(path, ticks, seed_ids, BASELINE_DECODER, disconnected=True),
            'no_input': evaluate_condition(path, ticks, seed_ids, BASELINE_DECODER, drive_enabled=False),
            'shuffled': aggregate(
                [run_trial(path, ticks, seed, BASELINE_DECODER, shuffle_seed=seed) for seed in seed_ids],
                extra={'decoder': dict(BASELINE_DECODER)},
            ),
        },
    }


def compact_condition(condition):
    return {key: value for key, value in condition.items() if key != 'runs'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph')
    parser.add_argument('--ticks', type=int, default=500)
    parser.add_argument('--development-seeds', type=int, default=10)
    parser.add_argument('--held-out-seeds', type=int, default=10)
    parser.add_argument('--out', default='experiment.json')
    args = parser.parse_args()
    try:
        result = decoder_experiment(args.graph, args.ticks, args.development_seeds, args.held_out_seeds)
        Path(args.out).write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        summary = {
            'selection': result['selection'],
            'development': {item['decoder']['name']: compact_condition({k: v for k, v in item.items() if k != 'decoder'})
                            for item in result['development_sweep']},
            'held_out': {name: compact_condition(condition) for name, condition in result['held_out'].items()},
        }
        print(json.dumps(summary, indent=2, default=lambda value: list(value) if isinstance(value, tuple) else value))
    except (ValueError, OSError) as exc:
        parser.exit(2, f'Error: {exc}\n')
