"""Synthetic gift checks. A transfer is not evidence of cooperation or friendship."""
import unittest
from pathlib import Path
from ecosystem import exchange_gifts, rules_from
from gift_experiment import compare


class GiftTests(unittest.TestCase):
    def agents(self):
        return [
            {'id': 0, 'x': 0.0, 'y': 0.0, 'alive': True, 'energy': 1.0},
            {'id': 1, 'x': 1.0, 'y': 0.0, 'alive': True, 'energy': 0.4},
            {'id': 2, 'x': 30.0, 'y': 0.0, 'alive': True, 'energy': 1.0},
        ]

    def test_transfer_loses_energy_and_checks_later_survival(self):
        rules = rules_from({'gifts': True, 'gift_chance': 1, 'gift_cooldown': 5, 'gift_range': 5,
                            'gift_amount': 0.15, 'gift_keep': 0.10, 'gift_follow': 2})
        agents = self.agents()
        events = []
        self.assertEqual(exchange_gifts(agents, 0, rules, events), 2)
        self.assertAlmostEqual(agents[0]['energy'], 0.95)
        self.assertAlmostEqual(agents[1]['energy'], 0.35)
        self.assertEqual(agents[2]['energy'], 1.0)
        self.assertLess(agents[0]['gift_gained'], agents[0]['gift_paid'])
        self.assertLess(agents[1]['gift_gained'], agents[1]['gift_paid'])
        self.assertEqual(exchange_gifts(agents, 1, rules, events), 0)
        agents[1]['alive'] = False
        exchange_gifts(agents, 2, rules, events)
        self.assertEqual(agents[0]['gift_checks'], 1)
        self.assertEqual(agents[0]['gift_alive_later'], 0)
        self.assertEqual(events[0]['kind'], 'gift')

    def test_disabled_gifts_do_not_move_energy(self):
        rules = rules_from({'gifts': False, 'gift_chance': 1, 'gift_range': 40})
        agents = self.agents()
        before = [agent['energy'] for agent in agents]
        self.assertEqual(exchange_gifts(agents, 0, rules, []), 0)
        self.assertEqual([agent['energy'] for agent in agents], before)
        with self.assertRaises(ValueError):
            rules_from({'gift_keep': 0.2, 'gift_amount': 0.15})

    def test_paired_runs_are_repeatable(self):
        graph = Path(__file__).resolve().parents[1] / 'demo.json'
        first = compare(graph, [0], ticks=6)
        self.assertEqual(first, compare(graph, [0], ticks=6))
        self.assertEqual([row['gifts'] for row in first['rows']], [False, True])
        self.assertFalse(first['hazards'])
        with self.assertRaises(ValueError):
            compare(graph, [1, 1], ticks=6)
