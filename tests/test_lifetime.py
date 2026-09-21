"""Synthetic lifetime-learning checks. Scores are individual state, not genes or synapses."""
import unittest
from pathlib import Path
from ecosystem import (action_score, exchange_gifts, gift_willing, learn_action, resolve_predation,
                       rules_from, scavenge_corpses, settle_attack_learning)
from lifetime_experiment import compare

DEMO = Path(__file__).resolve().parents[1] / 'demo.json'


class LifetimeTests(unittest.TestCase):
    def test_gift_energy_moves_the_score_and_not_the_gene(self):
        rules = rules_from({'gifts': True, 'gift_chance': 1, 'gift_follow': 5, 'gift_range': 5,
                            'gift_cooldown': 1, 'lifetime_learning': True})
        donor = {'id': 0, 'x': 0.0, 'y': 0.0, 'alive': True, 'energy': 1.0, 'genome': {'generosity': 1.2}}
        neighbour = {'id': 1, 'x': 1.0, 'y': 0.0, 'alive': True, 'energy': 0.4, 'genome': {'generosity': 0.0}}
        self.assertEqual(exchange_gifts([donor, neighbour], 0, rules, []), 1)
        paid = donor['energy']
        donor['energy'] = paid + 0.05
        exchange_gifts([donor, neighbour], 5, rules, [])
        self.assertGreater(action_score(donor, 'gift', 5, rules), 0.5)
        self.assertEqual(donor['action_learning']['gift']['seen_useful'], 1)
        self.assertEqual(donor['genome']['generosity'], 1.2)
        child = {'genome': dict(donor['genome'])}
        self.assertAlmostEqual(action_score(child, 'gift', 5, rules), 0.5)
        self.assertIsNone(learn_action(donor, 'gift', 6, 'empty', rules_from({'lifetime_learning': False})))
        self.assertEqual(donor['action_learning']['gift']['seen_empty'], 0)

    def test_low_score_blocks_an_attempt_the_neutral_prior_allows(self):
        rules = rules_from({'gifts': True, 'gift_chance': 0.4, 'lifetime_learning': True})
        neutral = {'id': 0, 'genome': {'generosity': 1.0}}
        taught = {'id': 0, 'genome': {'generosity': 1.0}}
        for tick in range(8):
            learn_action(taught, 'gift', tick, 'empty', rules)
        tick = next(t for t in range(30, 80) if gift_willing(neutral, t, rules) and not gift_willing(taught, t, rules))
        self.assertGreater(tick, 0)
        off = rules_from({'lifetime_learning': False, 'gifts': True, 'gift_chance': 0.4})
        self.assertEqual(gift_willing(taught, tick, off), gift_willing(neutral, tick, rules))

    def test_eating_a_kill_is_useful_and_a_missed_corpse_is_not(self):
        rules = rules_from({'predation': True, 'attack_chance': 1, 'attack_cooldown': 1, 'attack_floor': 0,
                            'attack_range': 2, 'sense_range': 12, 'scavenging': True, 'scavenge_below': 2,
                            'eat_radius': 0.55, 'corpse_ticks': 10, 'lifetime_learning': True})
        attacker = {'id': 0, 'x': 0.0, 'y': 0.0, 'alive': True, 'energy': 1.0, 'meals': 0, 'genome': {'aggression': 1.0}}
        target = {'id': 1, 'x': 1.0, 'y': 0.0, 'alive': True, 'energy': 0.2}
        self.assertEqual(resolve_predation([attacker, target], [], 0, rules, []), 1)
        self.assertEqual(scavenge_corpses([attacker, target], 0, rules, []), 0)
        attacker['x'] = 0.5
        self.assertEqual(scavenge_corpses([attacker, target], 1, rules, []), 1)
        settle_attack_learning([attacker, target], 1, rules)
        self.assertEqual(attacker['action_learning']['attack']['seen_useful'], 1)
        self.assertEqual(attacker['attack_pending'], [])
        self.assertEqual(attacker['genome']['aggression'], 1.0)

        missed = {'id': 0, 'x': 5.0, 'y': 0.0, 'alive': True, 'energy': 1.0, 'genome': {'aggression': 1.0}}
        victim = {'id': 1, 'x': 6.0, 'y': 0.0, 'alive': True, 'energy': 0.2}
        resolve_predation([missed, victim], [], 0, rules, [])
        for tick in range(1, 11):
            settle_attack_learning([missed, victim], tick, rules)
        self.assertAlmostEqual(action_score(missed, 'attack', 11, rules), 0.5)
        self.assertEqual(missed['attack_pending'], [])

    def test_arrival_after_someone_else_ate_is_empty(self):
        rules = rules_from({'predation': True, 'attack_chance': 1, 'attack_floor': 0, 'attack_range': 2,
                            'sense_range': 12, 'scavenging': True, 'scavenge_below': 2, 'eat_radius': 0.55,
                            'corpse_ticks': 30, 'lifetime_learning': True})
        killer = {'id': 0, 'x': 0.0, 'y': 0.0, 'alive': True, 'energy': 1.0, 'genome': {'aggression': 1.0}}
        victim = {'id': 1, 'x': 1.0, 'y': 0.0, 'alive': True, 'energy': 0.2}
        rival = {'id': 2, 'x': 1.0, 'y': 0.0, 'alive': True, 'energy': 0.4, 'ate': False}
        resolve_predation([killer, victim, rival], [], 0, rules, [])
        self.assertEqual(scavenge_corpses([killer, victim, rival], 1, rules, []), 1)
        killer['x'] = 1.0
        settle_attack_learning([killer, victim, rival], 2, rules)
        self.assertEqual(killer['action_learning']['attack']['seen_empty'], 1)
        self.assertLess(action_score(killer, 'attack', 2, rules), 0.5)

    def test_evidence_decays_toward_neutral(self):
        rules = rules_from({'lifetime_learning': True})
        agent = {'id': 3, 'genome': {}}
        self.assertAlmostEqual(learn_action(agent, 'gift', 0, 'useful', rules), 2 / 3)
        self.assertAlmostEqual(action_score(agent, 'gift', 400, rules), 0.6)

    def test_paired_runs_are_repeatable(self):
        first = compare(DEMO, [0], ticks=8)
        self.assertEqual(first, compare(DEMO, [0], ticks=8))
        self.assertEqual([row['lifetime_learning'] for row in first['rows']], [False, True])
        self.assertEqual(first['rows'][0]['gift_useful'], 0)
        self.assertEqual(first['rows'][0]['attack_useful'], 0)
        with self.assertRaises(ValueError):
            compare(DEMO, [1, 1], ticks=8)
