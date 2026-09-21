"""One personality gene at a time. The other two stay at their neutral scale of 1."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from ecosystem import simulate_ecosystem


GENES = ('caution', 'generosity', 'aggression')
OUTCOMES = ('alive', 'births', 'gifts', 'attacks', 'hazard_entries')
FIXED = dict(hazards=True, seasons=True, scavenging=True, gifts=True, predation=True, social_learning=True)


def compare(graph, seeds, ticks=2000, sense_range=12):
    seeds = list(seeds)
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError('provide distinct seeds')
    rows = []
    for seed in seeds:
        frozen_world = _run(graph, seed, ticks, sense_range, GENES)
        for gene in GENES:
            rows.append(_row(seed, gene, False, frozen_world))
            rows.append(_row(seed, gene, True, _run(graph, seed, ticks, sense_range, tuple(name for name in GENES if name != gene))))
    means = {}
    for gene in GENES:
        means[gene] = {
            'frozen': _means(rows, gene, False),
            'varying': _means(rows, gene, True),
        }
    return dict(
        ablation='personality', graph=str(graph),
        graph_sha256=hashlib.sha256(Path(graph).read_bytes()).hexdigest(),
        ticks=ticks, seeds=seeds, sense_range=sense_range, fixed=FIXED, genes=list(GENES),
        decoder=dict(turn_sign=-1, turn_gain=1), rows=rows, means=means,
        caveat='Exploratory paired-seed comparison, not biological validation. Hazards, seasons, '
               'scavenging, gifts, predation, and sender learning stay on. One gene mutates; the other '
               'two stay at 1, which leaves the current attempt chances and hazard comparison unchanged. '
               'These genes are inherited scales, not character traits. The circuit gains no new output. '
               'No confidence intervals. Python and browser RNGs differ.')


def _run(graph, seed, ticks, sense_range, frozen):
    result = simulate_ecosystem(
        graph, ticks, seed, sense_range=sense_range, turn_sign=-1, turn_gain=1,
        record_every=ticks, frozen_genes=list(frozen), **FIXED)
    final = result['final']
    return dict(
        alive=final['alive'], births=final['births'], gifts=final['gifts']['sent'],
        attacks=final['attacks'], hazard_entries=final['hazard_entries'],
        personality_mean=final['personality_mean'])


def _row(seed, gene, varying, outcome):
    return dict(
        seed=seed, gene=gene, varying=varying, alive=outcome['alive'], births=outcome['births'],
        gifts=outcome['gifts'], attacks=outcome['attacks'], hazard_entries=outcome['hazard_entries'],
        gene_mean=outcome['personality_mean'][gene])


def _means(rows, gene, varying):
    chosen = [row for row in rows if row['gene'] == gene and row['varying'] is varying]
    summary = {key: round(mean(row[key] for row in chosen), 4) for key in OUTCOMES}
    summary['gene_mean'] = round(mean(row['gene_mean'] for row in chosen), 4)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph')
    parser.add_argument('--seeds', default='0,1,2,3,4')
    parser.add_argument('--ticks', type=int, default=2000)
    parser.add_argument('--sense-range', type=float, default=12)
    parser.add_argument('--out', default='personality-comparison.json')
    args = parser.parse_args()
    report = compare(args.graph, [int(part) for part in args.seeds.split(',')], args.ticks, args.sense_range)
    Path(args.out).write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report['means'], indent=2))
