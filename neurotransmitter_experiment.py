"""Held-out foraging comparison for DNg13 transmitter signs.

All-positive weights, signs from the aggregate table, and a shuffle of the
applied signs. This is an interface result, not evidence of biological foraging
or inhibition. The live ecosystem stays on the all-positive controller.
"""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from experiments import run_trial
from neurotransmitter import (CONFIDENCE_THRESHOLD, assignments, load_table, multipliers,
                              shuffle_multipliers)
from sim import Circuit


HELD_OUT_SEEDS = list(range(10, 20))
DECODER = {'name': 'sensory+1_turn-1_gain1.00', 'turn_sign': -1, 'turn_gain': 1.0, 'sensory_sign': 1}
SHUFFLE_SEED = 0
TABLE = Path(__file__).resolve().parent / 'circuits' / 'dng13-neurotransmitters.json'


def motor_probe(graph, signs):
    circuit = Circuit(graph, signs=signs)
    quiet = Circuit(graph, signs=signs)
    drives = [0.5 if node['role'] == 'sensory' else 0.0 for node in circuit.nodes]
    zeros = [0.0] * len(circuit.nodes)
    for _ in range(200):
        circuit.step(drives)
        quiet.step(zeros)
    left, right = circuit.motors()
    still_left, still_right = quiet.motors()
    return {
        'input_on_left': left, 'input_on_right': right,
        'input_off_left': still_left, 'input_off_right': still_right,
        'moves_when_input_is_on': (left + right) > (still_left + still_right),
    }


def compare(graph, ticks=500, seeds=None, shuffle_seed=SHUFFLE_SEED):
    seeds = list(HELD_OUT_SEEDS if seeds is None else seeds)
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError('provide distinct seeds')
    if type(ticks) is not int or ticks < 1:
        raise ValueError('ticks must be a positive integer')
    path = Path(graph)
    loaded = json.loads(path.read_text())
    table = load_table(TABLE)
    rows = assignments(table, [node['id'] for node in loaded['nodes']])
    signed = multipliers(rows)
    shuffled = shuffle_multipliers(rows, shuffle_seed)
    conditions = {
        'all_positive': None,
        'signed': signed,
        'sign_shuffled': shuffled,
    }
    reports = {}
    for name, signs in conditions.items():
        runs = [run_trial(path, ticks, seed, DECODER, signs=signs) for seed in seeds]
        probe = motor_probe(loaded, signs)
        reports[name] = {
            'mean_food_collected': mean(run['food_collected'] for run in runs),
            'mean_motor_activity': mean(run['mean_motor_activity'] for run in runs),
            'food_collected': [run['food_collected'] for run in runs],
            'moves_when_input_is_on': probe['moves_when_input_is_on'],
            'probe': probe,
        }
    dropped = sum(1 for edge in loaded['edges'] if signed.get(str(edge['pre']), 1) == 0)
    return {
        'ablation': 'neurotransmitter_signs',
        'graph': str(path),
        'graph_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'table': str(TABLE),
        'table_source_sha256': table['source_sha256'],
        'confidence_threshold': CONFIDENCE_THRESHOLD,
        'ticks': ticks,
        'seeds': seeds,
        'decoder': DECODER,
        'shuffle_seed': shuffle_seed,
        'shuffle_identical_to_signed': shuffled == signed,
        'neurons': rows,
        'edges_dropped': dropped,
        'conditions': reports,
        'caveat': 'Exploratory held-out comparison, not biological validation. Acetylcholine at or above '
                  '0.5 stays positive, GABA at or above 0.5 becomes negative, and glutamate edges are dropped. '
                  'Monoamines would be recorded and not applied. The rate update still clips activity at 0. '
                  'Ground truth in the table is not the sign rule. A foraging change is an interface result. '
                  'The live page keeps the all-positive controller. No confidence intervals.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph')
    parser.add_argument('--ticks', type=int, default=500)
    parser.add_argument('--out', default='neurotransmitter-comparison.json')
    args = parser.parse_args()
    report = compare(args.graph, args.ticks)
    Path(args.out).write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({name: {key: row[key] for key in ('mean_food_collected', 'mean_motor_activity', 'moves_when_input_is_on')}
                      for name, row in report['conditions'].items()}, indent=2))
    print('shuffle_identical', report['shuffle_identical_to_signed'], 'dropped', report['edges_dropped'])
