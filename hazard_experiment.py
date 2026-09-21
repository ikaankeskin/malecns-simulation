"""CPU-only hazard on/off ablation; engineered terrain, not biology."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from ecosystem import simulate_ecosystem


OUTCOMES = ('alive', 'births', 'meals', 'hazard', 'starved', 'old_age')


def compare(graph, seeds, ticks=2000, sense_range=12):
    seeds = list(seeds)
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError('provide distinct seeds')
    rows = []
    result = None
    for seed in seeds:
        for enabled in (False, True):
            result = simulate_ecosystem(
                graph, ticks, seed, hazards=enabled, sense_range=sense_range,
                turn_sign=-1, turn_gain=1, record_every=ticks)
            final = result['final']
            rows.append(dict(
                seed=seed, hazards=enabled, alive=final['alive'], births=final['births'],
                meals=final['meals'], hazard=final['hazard'], starved=final['starved'],
                old_age=final['old_age']))
    means = {
        name: {key: mean(row[key] for row in rows if row['hazards'] is enabled) for key in OUTCOMES}
        for name, enabled in (('off', False), ('on', True))
    }
    rules = dict(result['rules'])
    rules.pop('hazards', None)
    return dict(
        ablation='hazards', graph=str(graph),
        graph_sha256=hashlib.sha256(Path(graph).read_bytes()).hexdigest(),
        ticks=ticks, seeds=seeds, sense_range=sense_range,
        decoder=dict(turn_sign=-1, turn_gain=1), rules=rules, rows=rows, means=means,
        caveat='Exploratory paired-seed comparison, not biological validation. Seasons and scavenging '
               'stay at their defaults. Hazard discs use a separate placement stream, so food placement '
               'matches the off cell until behaviour diverges. Deaths in a disc are labelled hazard, '
               'not injury or evolved avoidance. No confidence intervals. Python and browser RNGs differ.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph')
    parser.add_argument('--seeds', default='0,1,2,3,4')
    parser.add_argument('--ticks', type=int, default=2000)
    parser.add_argument('--sense-range', type=float, default=12)
    parser.add_argument('--out', default='hazard-comparison.json')
    args = parser.parse_args()
    report = compare(args.graph, [int(part) for part in args.seeds.split(',')], args.ticks, args.sense_range)
    Path(args.out).write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report['means'], indent=2))
