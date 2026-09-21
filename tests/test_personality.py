"""Synthetic personality checks. The genes are scales, not character traits."""
import random
import unittest
from pathlib import Path
from ecosystem import (BASE_GENOME, attack_willing, compete_hazard, exchange_gifts, gift_willing,
                       inherit_genome, resolve_predation, rules_from, simulate_ecosystem)
from personality_experiment import GENES, compare

DEMO = Path(__file__).resolve().parents[1] / 'demo.json'


class PersonalityTests(unittest.TestCase):
    def test_caution_changes_whether_a_hazard_beats_food(self):
        rules = rules_from({'hazards': True, 'sense_range': 12})
        agent = {'x': 0.0, 'y': 0.0, 'heading': 0.0, 'genome': {'caution': 1.0}}
        food = {'x': 2.0, 'y': 0.0, 'kind': 'foraging'}
        disc = {'id': 0, 'x': 6.0, 'y': 0.0, 'radius': 3.5}
        self.assertEqual(compete_hazard(agent, food, [disc], rules)['kind'], 'foraging')
        agent['genome']['caution'] = 2.0
        self.assertEqual(compete_hazard(agent, food, [disc], rules)['kind'], 'avoiding_hazard')
        agent['genome']['caution'] = 0.0
        inside = {'id': 1, 'x': 0.0, 'y': 0.0, 'radius': 3.5}
        self.assertEqual(compete_hazard(agent, food, [inside], rules)['kind'], 'avoiding_hazard')

    def test_generosity_and_aggression_scale_attempt_chance(self):
        rules = rules_from({'gifts': True, 'gift_chance': 0.25, 'gift_range': 5, 'gift_cooldown': 1,
                            'predation': True, 'attack_chance': 0.35, 'attack_range': 2,
                            'attack_cooldown': 1, 'attack_floor': 0.0, 'sense_range': 12})
        donor = {'id': 0, 'x': 0.0, 'y': 0.0, 'alive': True, 'energy': 1.0, 'genome': {'generosity': 1.0}}
        tick = next(t for t in range(400)
                    if not gift_willing(donor, t, rules)
                    and gift_willing({**donor, 'genome': {'generosity': 2.0}}, t, rules))
        neighbour = {'id': 1, 'x': 1.0, 'y': 0.0, 'alive': True, 'energy': 1.0, 'genome': {'generosity': 0.0}}
        self.assertEqual(exchange_gifts([donor, neighbour], tick, rules, []), 0)
        donor['last_gift'] = -10 ** 9
        donor['genome']['generosity'] = 2.0
        self.assertEqual(exchange_gifts([donor, neighbour], tick, rules, []), 1)
        donor['genome']['generosity'] = 0.0
        donor['last_gift'] = -10 ** 9
        self.assertEqual(exchange_gifts([donor, neighbour], tick, rules_from({'gifts': True, 'gift_chance': 1, 'gift_range': 5}), []), 0)

        attacker = {'id': 0, 'x': 0.0, 'y': 0.0, 'alive': True, 'energy': 1.0, 'genome': {'aggression': 1.0}}
        attack_tick = next(t for t in range(400)
                            if not attack_willing(attacker, t, rules)
                            and attack_willing({**attacker, 'genome': {'aggression': 2.0}}, t, rules))
        target = {'id': 1, 'x': 1.0, 'y': 0.0, 'alive': True, 'energy': 1.0, 'genome': {'aggression': 0.0}}
        self.assertEqual(resolve_predation([attacker, target], [], attack_tick, rules, []), 0)
        self.assertEqual(attacker['attacks'], 0)
        attacker['last_attack'] = -10 ** 9
        attacker['genome']['aggression'] = 2.0
        resolve_predation([attacker, target], [], attack_tick, rules, [])
        self.assertEqual(attacker['attacks'], 1)

    def test_frozen_gene_stays_neutral_while_others_can_change(self):
        rules = {'mutation_rate': 1.0, 'mutation_sigma': 0.3, 'frozen_genes': ['caution']}
        child, mutations = inherit_genome(dict(BASE_GENOME), dict(BASE_GENOME), random.Random(4), rules)
        self.assertEqual(child['caution'], 1.0)
        self.assertNotIn('caution', mutations)
        self.assertTrue(any(gene in mutations for gene in ('generosity', 'aggression')))
        with self.assertRaises(ValueError):
            rules_from({'frozen_genes': ['bravery']})

    def test_entries_count_once_while_an_agent_stays_inside(self):
        result = simulate_ecosystem(
            DEMO, 3, 0, agents=1, patches=1, map_half=10, hazards=True, hazard_count=1,
            hazard_radius=30, hazard_drain=0.001, disconnected=True, base_drain=0.0, move_cost=0.0)
        self.assertEqual(result['final']['hazard_entries'], 1)
        self.assertEqual(set(GENES), {'caution', 'generosity', 'aggression'})

    def test_paired_runs_are_repeatable(self):
        first = compare(DEMO, [0], ticks=6)
        self.assertEqual(first, compare(DEMO, [0], ticks=6))
        self.assertEqual(len(first['rows']), 6)
        frozen = [row for row in first['rows'] if not row['varying']]
        self.assertTrue(all(row['gene_mean'] == 1.0 for row in frozen))
        self.assertEqual(frozen[0]['gifts'], frozen[1]['gifts'])
        with self.assertRaises(ValueError):
            compare(DEMO, [0, 0], ticks=6)
