"""Gift and attack scores stay on the individual. They are not inherited and do not change synapses.

Pre-registered outcomes, fixed before the paired runs:

- Gift: 100 ticks later, a living donor compares their energy with the energy recorded just after they paid. Greater or equal is useful. Lower is empty. Other donors are not a control. Recipient survival is counted separately and does not train the score.
- Attack: only a killing blow opens a record. Eating that corpse is useful. Reaching its position after it is gone is empty. If the corpse window ends before the attacker gets there, the record is dropped and the score stays put. A non-killing hit adds nothing.
"""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from ecosystem import simulate_ecosystem


OUTCOMES = ('alive', 'births', 'gifts', 'attacks', 'hazard_entries',
            'gift_useful', 'gift_empty', 'attack_useful', 'attack_empty')
FIXED = dict(
    hazards=True, seasons=True, scavenging=True, gifts=True, predation=True, social_learning=True,
    frozen_genes=['caution', 'generosity', 'aggression'])


def compare(graph, seeds, ticks=2000, sense_range=12):
    seeds = list(seeds)
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError('provide distinct seeds')
    rows = []
    for seed in seeds:
        for enabled in (False, True):
            result = simulate_ecosystem(
                graph, ticks, seed, lifetime_learning=enabled, sense_range=sense_range,
                turn_sign=-1, turn_gain=1, record_every=ticks, **FIXED)
            final = result['final']
            actions = final['actions']
            rows.append(dict(
                seed=seed, lifetime_learning=enabled, alive=final['alive'], births=final['births'],
                gifts=final['gifts']['sent'], attacks=final['attacks'], hazard_entries=final['hazard_entries'],
                gift_useful=actions['gift_useful'], gift_empty=actions['gift_empty'],
                attack_useful=actions['attack_useful'], attack_empty=actions['attack_empty']))
    means = {
        name: {key: round(mean(row[key] for row in rows if row['lifetime_learning'] is enabled), 4) for key in OUTCOMES}
        for name, enabled in (('off', False), ('on', True))
    }
    return dict(
        ablation='lifetime_learning', graph=str(graph),
        graph_sha256=hashlib.sha256(Path(graph).read_bytes()).hexdigest(),
        ticks=ticks, seeds=seeds, sense_range=sense_range, fixed=FIXED,
        proxy=dict(
            gift='Living donor energy at 100 ticks versus energy just after the gift. No comparison with other donors.',
            attack='Eat own kill, or arrive after that corpse is gone. An unreached corpse adds no evidence.'),
        decoder=dict(turn_sign=-1, turn_gain=1), rows=rows, means=means,
        caveat='Exploratory paired-seed comparison, not biological validation. Hazards, seasons, scavenging, '
               'gifts, predation, and sender learning stay on. Personality genes stay at 1. Learning off keeps '
               'the neutral score, so attempt chances match the inherited genes. Scores are not inherited and '
               'do not change synapses. No confidence intervals. Python and browser RNGs differ.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph')
    parser.add_argument('--seeds', default='0,1,2,3,4')
    parser.add_argument('--ticks', type=int, default=2000)
    parser.add_argument('--sense-range', type=float, default=12)
    parser.add_argument('--out', default='lifetime-comparison.json')
    args = parser.parse_args()
    report = compare(args.graph, [int(part) for part in args.seeds.split(',')], args.ticks, args.sense_range)
    Path(args.out).write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report['means'], indent=2))
