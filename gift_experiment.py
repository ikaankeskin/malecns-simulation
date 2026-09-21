"""CPU-only gift on/off ablation. A higher alive count is not cooperation."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from ecosystem import simulate_ecosystem


OUTCOMES = ('alive', 'births', 'meals', 'sent', 'energy_paid', 'energy_gained', 'alive_later')


def compare(graph, seeds, ticks=2000, sense_range=12):
    seeds = list(seeds)
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError('provide distinct seeds')
    rows = []
    result = None
    for seed in seeds:
        for enabled in (False, True):
            result = simulate_ecosystem(
                graph, ticks, seed, gifts=enabled, hazards=False, sense_range=sense_range,
                turn_sign=-1, turn_gain=1, record_every=ticks)
            final = result['final']
            gifts = final['gifts']
            rows.append(dict(
                seed=seed, gifts=enabled, alive=final['alive'], births=final['births'],
                meals=final['meals'], sent=gifts['sent'], energy_paid=gifts['energy_paid'],
                energy_gained=gifts['energy_gained'], alive_later=gifts['alive_later']))
    means = {
        name: {key: mean(row[key] for row in rows if row['gifts'] is enabled) for key in OUTCOMES}
        for name, enabled in (('off', False), ('on', True))
    }
    return dict(
        ablation='gifts', graph=str(graph),
        graph_sha256=hashlib.sha256(Path(graph).read_bytes()).hexdigest(),
        ticks=ticks, seeds=seeds, sense_range=sense_range, hazards=False,
        decoder=dict(turn_sign=-1, turn_gain=1), rows=rows, means=means,
        caveat='Exploratory paired-seed comparison, not biological validation. Hazards are off. '
               'Communication and sender learning stay at their defaults. The recipient gains less '
               'than the donor pays. alive_later counts whether the recipient is alive 100 ticks after '
               'the gift; it does not show that the gift saved them. No confidence intervals. '
               'Python and browser RNGs differ.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph')
    parser.add_argument('--seeds', default='0,1,2,3,4')
    parser.add_argument('--ticks', type=int, default=2000)
    parser.add_argument('--sense-range', type=float, default=12)
    parser.add_argument('--out', default='gift-comparison.json')
    args = parser.parse_args()
    report = compare(args.graph, [int(part) for part in args.seeds.split(',')], args.ticks, args.sense_range)
    Path(args.out).write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report['means'], indent=2))
