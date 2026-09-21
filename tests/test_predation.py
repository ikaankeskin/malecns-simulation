"""Synthetic attack checks. A kill is not a meal, and the circuit has no attack output."""
import unittest
from pathlib import Path
from ecosystem import resolve_predation, rules_from
from predation_experiment import compare

DEMO = Path(__file__).resolve().parents[1] / 'demo.json'


class PredationTests(unittest.TestCase):
    def rules(self):
        return rules_from({'predation': True, 'attack_chance': 1, 'attack_cooldown': 5,
                           'attack_range': 2, 'attack_cost': 0.08, 'attack_damage': 0.45,
                           'attack_floor': 0.5, 'corpse_ticks': 180, 'sense_range': 12})

    def test_closer_neighbour_can_be_killed_without_feeding_the_attacker(self):
        rules = self.rules()
        attacker = {'id': 0, 'x': 0.0, 'y': 0.0, 'alive': True, 'energy': 1.0, 'meals': 0}
        target = {'id': 1, 'x': 1.0, 'y': 0.0, 'alive': True, 'energy': 0.2, 'meals': 3}
        events = []
        self.assertEqual(resolve_predation([attacker, target], [], 0, rules, events), 1)
        self.assertAlmostEqual(attacker['energy'], 0.92)
        self.assertEqual(attacker['meals'], 0)
        self.assertFalse(target['alive'])
        self.assertEqual(target['cause_of_death'], 'predation')
        self.assertEqual(target['corpse_until'], 180)
        self.assertEqual(resolve_predation([attacker, target], [], 1, rules, events), 0)
        wounded = {'id': 1, 'x': 1.0, 'y': 0.0, 'alive': True, 'energy': 1.0}
        attacker['last_attack'] = -10 ** 9
        self.assertEqual(resolve_predation([attacker, wounded], [], 0, rules, []), 0)
        self.assertTrue(wounded['alive'])
        self.assertIsNone(wounded.get('cause_of_death'))

    def test_food_closer_than_a_neighbour_blocks_the_attack(self):
        rules = self.rules()
        attacker = {'id': 0, 'x': 0.0, 'y': 0.0, 'alive': True, 'energy': 1.0}
        target = {'id': 1, 'x': 1.5, 'y': 0.0, 'alive': True, 'energy': 0.2}
        food = [{'id': 0, 'x': 0.4, 'y': 0.0, 'stage': 'mature'}]
        self.assertEqual(resolve_predation([attacker, target], food, 0, rules, []), 0)
        self.assertEqual(attacker['energy'], 1.0)
        self.assertTrue(target['alive'])
        far = {'id': 1, 'x': 5.0, 'y': 0.0, 'alive': True, 'energy': 0.2}
        self.assertEqual(resolve_predation([attacker, far], [], 0, rules, []), 0)
        off = rules_from({'predation': False, 'attack_chance': 1, 'sense_range': 12})
        self.assertEqual(resolve_predation([attacker, target], [], 0, off, []), 0)
        with self.assertRaises(ValueError):
            rules_from({'attack_range': 30, 'sense_range': 12})

    def test_paired_runs_are_repeatable(self):
        first = compare(DEMO, [0], ticks=6)
        self.assertEqual(first, compare(DEMO, [0], ticks=6))
        self.assertEqual([row['predation_enabled'] for row in first['rows']], [False, True])
        self.assertTrue(first['fixed']['hazards'])
        self.assertFalse(first['fixed']['gifts'])
        with self.assertRaises(ValueError):
            compare(DEMO, [1, 1], ticks=6)
