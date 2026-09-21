"""Synthetic hazard fixtures. Discs are engineered terrain, not fly physiology."""
import unittest
from pathlib import Path
from ecosystem import (compete_hazard, resolve_death, rules_from, simulate_ecosystem, spawn_hazards)

DEMO = Path(__file__).resolve().parents[1] / 'demo.json'


class HazardTests(unittest.TestCase):
    def test_discs_stay_inside_and_do_not_move_food(self):
        rules = rules_from({})
        first = spawn_hazards(rules, 4)
        self.assertEqual(first, spawn_hazards(rules, 4))
        self.assertEqual(len(first), 3)
        self.assertEqual(spawn_hazards(rules_from({'hazards': False}), 4), [])
        for disc in first:
            self.assertLessEqual(abs(disc['x']) + disc['radius'], rules['map_half'] + 1e-6)
            self.assertLessEqual(abs(disc['y']) + disc['radius'], rules['map_half'] + 1e-6)
        off = simulate_ecosystem(DEMO, 1, 2, hazards=False, record_every=1)
        on = simulate_ecosystem(DEMO, 1, 2, hazards=True, record_every=1)
        self.assertEqual(off['ticks'][0]['patches'], on['ticks'][0]['patches'])
        self.assertEqual(on['hazards'], spawn_hazards(on['rules'], 2))

    def test_escape_wins_when_the_edge_is_closer_than_food(self):
        rules = rules_from({'sense_range': 12})
        agent = {'x': 0.0, 'y': 0.0, 'heading': 0.0}
        inside = {'id': 0, 'x': 2.0, 'y': 0.0, 'radius': 3.0}
        fled = compete_hazard(agent, {'x': 0.2, 'y': 0.0, 'kind': 'foraging'}, [inside], rules)
        self.assertEqual(fled['kind'], 'avoiding_hazard')
        self.assertLess(fled['x'], 0.0)
        edge = {'id': 0, 'x': 10.0, 'y': 0.0, 'radius': 1.0}
        self.assertEqual(compete_hazard(agent, {'x': 1.0, 'y': 0.0, 'kind': 'foraging'}, [edge], rules)['kind'], 'foraging')
        self.assertEqual(compete_hazard(agent, {'x': 11.0, 'y': 0.0, 'kind': 'foraging'}, [edge], rules)['kind'], 'avoiding_hazard')
        self.assertIsNone(compete_hazard(agent, None, [], rules_from({'hazards': False})))

    def test_death_order_and_disc_kill(self):
        rules = rules_from({})
        agent = {'energy': 0.0, 'age': 999, 'meals': 0, 'genome': {'lifespan': 1.0}}
        self.assertEqual(resolve_death(agent, rules, True, predation=True), 'predation')
        self.assertEqual(resolve_death(agent, rules, True), 'hazard')
        self.assertEqual(resolve_death(agent, rules, False), 'starvation')
        agent['energy'] = 1.0
        self.assertEqual(resolve_death(agent, rules, True), 'old_age')
        killed = simulate_ecosystem(
            DEMO, 3, 1, agents=2, patches=1, disconnected=True, hazards=True,
            hazard_radius=30, hazard_drain=5, base_drain=0, move_cost=0, max_age=1000,
            repro_rate=0, record_every=3)
        self.assertGreater(killed['final']['hazard'], 0)
        self.assertEqual(killed['final']['starved'], 0)
        self.assertTrue(any(event.get('cause') == 'hazard' for event in killed['events']))
