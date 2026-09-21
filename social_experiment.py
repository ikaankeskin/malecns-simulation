"""CPU-only communication ablation; engineered-world outcomes, not biology."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from ecosystem import simulate_ecosystem


def compare(graph, seeds, ticks=2000, sense_range=12):
    seeds = list(seeds)
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError('provide distinct seeds')
    rows = []
    for seed in seeds:
        for enabled in (False, True):
            result = simulate_ecosystem(graph, ticks, seed, communication=enabled,
                sense_range=sense_range, turn_sign=-1, turn_gain=1, record_every=20)
            final = result['final']
            rows.append(dict(seed=seed, communication=enabled,
                **{k: final[k] for k in ('alive', 'births', 'meals', 'peak', 'social')}))
    means = {name: {k: mean(r[k] for r in rows if r['communication'] == enabled)
                   for k in ('alive', 'births', 'meals', 'peak')}
             for name, enabled in [('off', False), ('on', True)]}
    return dict(graph=str(graph), graph_sha256=hashlib.sha256(Path(graph).read_bytes()).hexdigest(),
        ticks=ticks, seeds=seeds, sense_range=sense_range,
        decoder=dict(turn_sign=-1, turn_gain=1), rules=result['rules'], rows=rows, means=means,
        caveat='Exploratory paired-seed comparison, not biological validation. Communication toggles '
               'both signals and memory. Trajectories and subsequent world RNG draws can diverge; '
               'signal-associated meals are not causal attribution. No confidence intervals or '
               'held-out tuning claim. Python and browser RNGs differ.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph')
    parser.add_argument('--seeds', default='0,1,2,3,4')
    parser.add_argument('--ticks', type=int, default=2000)
    parser.add_argument('--sense-range', type=float, default=12)
    parser.add_argument('--out', default='social-comparison.json')
    args = parser.parse_args()
    report = compare(args.graph, [int(x) for x in args.seeds.split(',')], args.ticks, args.sense_range)
    Path(args.out).write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report['means'], indent=2))
