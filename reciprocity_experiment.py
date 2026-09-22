"""Paired recipient-policy comparison. Gifts stay on; only reciprocity varies."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from ecosystem import simulate_ecosystem


def compare(graph, seeds, ticks=2000):
    seeds = list(seeds)
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError('provide distinct seeds')
    rows = []
    for seed in seeds:
        for enabled in (False, True):
            result = simulate_ecosystem(graph, ticks, seed, gifts=True, reciprocity=enabled,
                hazards=False, predation=False, lifetime_learning=False, sense_range=12,
                turn_sign=-1, turn_gain=1, record_every=ticks)
            final = result['final']
            rows.append(dict(seed=seed, reciprocity=enabled,
                **{k: final[k] for k in ('alive', 'births', 'meals')},
                **{k: final['gifts'][k] for k in ('sent', 'returned_help', 'energy_paid', 'energy_gained')}))
    metrics = ('alive', 'births', 'meals', 'sent', 'returned_help', 'energy_paid', 'energy_gained')
    return dict(ablation='reciprocity', graph=str(graph),
        graph_sha256=hashlib.sha256(Path(graph).read_bytes()).hexdigest(),
        ticks=ticks, seeds=seeds, rules=result['rules'], rows=rows,
        means={name: {k: mean(r[k] for r in rows if r['reciprocity'] == enabled) for k in metrics}
               for name, enabled in [('off', False), ('on', True)]},
        caveat='Exploratory paired seeds, no confidence intervals or biological claim. Gifts stay on; '
        'only recipient preference changes. Rules describe the on condition; rows specify the toggle. '
        'Returned help counts gifts to remembered donors, even with preference off. It does not '
        'establish friendship or a survival benefit. No energy reward is added. Engines use different RNGs.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph')
    parser.add_argument('--seeds', default='0,1,2,3,4')
    parser.add_argument('--ticks', type=int, default=2000)
    parser.add_argument('--out', default='reciprocity-comparison.json')
    args = parser.parse_args()
    report = compare(args.graph, [int(s) for s in args.seeds.split(',')], args.ticks)
    Path(args.out).write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report['means'], indent=2))
