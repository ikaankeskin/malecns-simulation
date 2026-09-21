"""CPU-only seasons × scavenging ablation; engineered-world outcomes, not biology."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from ecosystem import simulate_ecosystem


OUTCOMES = ('alive', 'births', 'peak', 'meals', 'scavenged', 'living_founders')
CELLS = ((True, True), (True, False), (False, True), (False, False))


def _cell(seasons, scavenging):
    return f"seasons_{'on' if seasons else 'off'}_scavenging_{'on' if scavenging else 'off'}"


def compare(graph, seeds, ticks=2000, sense_range=12):
    seeds = list(seeds)
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError('provide distinct seeds')
    rows = []
    result = None
    for seed in seeds:
        for seasons, scavenging in CELLS:
            result = simulate_ecosystem(
                graph, ticks, seed, seasons=seasons, scavenging=scavenging,
                sense_range=sense_range, turn_sign=-1, turn_gain=1, record_every=ticks)
            final = result['final']
            living_founders = sum(1 for row in final['lineages'].values() if row['living'] > 0)
            rows.append(dict(
                seed=seed, seasons=seasons, scavenging=scavenging,
                alive=final['alive'], births=final['births'], peak=final['peak'],
                meals=final['meals'], scavenged=final['scavenged'],
                composted=final['composted'], living_founders=living_founders))
    means = {
        _cell(seasons, scavenging): {
            key: mean(row[key] for row in rows if row['seasons'] == seasons and row['scavenging'] == scavenging)
            for key in OUTCOMES
        }
        for seasons, scavenging in CELLS
    }
    rules = dict(result['rules'])
    rules.pop('seasons', None)
    rules.pop('scavenging', None)
    return dict(
        ablation='seasons_x_scavenging', graph=str(graph),
        graph_sha256=hashlib.sha256(Path(graph).read_bytes()).hexdigest(),
        ticks=ticks, seeds=seeds, sense_range=sense_range,
        decoder=dict(turn_sign=-1, turn_gain=1), rules=rules, rows=rows, means=means,
        caveat='Exploratory 2×2 paired-seed comparison, not biological validation. '
               'Composting stays enabled when scavenging is off. Plant meals and scavenged '
               'meals are counted separately. Living founders are lineages with at least one '
               'living descendant. Trajectories diverge across cells, so differences are not '
               'causal attribution. No confidence intervals or held-out tuning claim. '
               'Python and browser RNGs differ.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph')
    parser.add_argument('--seeds', default='0,1,2,3,4')
    parser.add_argument('--ticks', type=int, default=2000)
    parser.add_argument('--sense-range', type=float, default=12)
    parser.add_argument('--out', default='ecology-comparison.json')
    args = parser.parse_args()
    report = compare(args.graph, [int(part) for part in args.seeds.split(',')], args.ticks, args.sense_range)
    Path(args.out).write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report['means'], indent=2))
