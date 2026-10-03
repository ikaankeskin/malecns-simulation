"""Synthetic capacity/determinism checks; not biological validation."""
import unittest
from unittest.mock import patch
import gardening
from ecosystem import simulate_ecosystem


def carrier(agent_id, **overrides):
    return dict(id=agent_id, alive=True, x=10.0+agent_id*3, y=0.0,
                energy=1.0, planted=0, carried_seed=dict(tick=0, until=600,
                x=0.0, y=0.0, source_patch=0, root_patch=0, plant_generation=1), **overrides)


class GardenCapacityTests(unittest.TestCase):
    def test_full_garden_skips_spacing_but_expires_seeds(self):
        patches = [dict(id=i, planter=0, x=0.0, y=0.0) for i in range(gardening.MAX_GARDENS)]
        living, expired, dead = carrier(0), carrier(1), carrier(2)
        expired['carried_seed']['until'] = 20
        dead['alive'] = False
        events = []
        with patch('gardening.math.hypot', side_effect=AssertionError('full garden scanned')):
            gardening.plant_seeds([living, expired, dead], patches, 20,
                                  dict(gardening=True), events)
        self.assertIsNotNone(living['carried_seed'])
        self.assertIsNone(expired['carried_seed'])
        self.assertIsNone(dead['carried_seed'])
        self.assertEqual(living['energy'], 1.0)
        self.assertEqual(events, [])

    def test_last_slot_goes_to_first_eligible_id_and_no_more(self):
        patches = [dict(id=i, planter=0, x=0.0, y=0.0) for i in range(gardening.MAX_GARDENS-1)]
        first, second = carrier(0), carrier(1)
        events = []
        gardening.plant_seeds([second, first], patches, 20,
                              dict(gardening=True, map_half=80, seed_ticks=10), events)
        self.assertEqual(len(patches), gardening.MAX_GARDENS)
        self.assertEqual(patches[-1]['planter'], first['id'])
        self.assertIsNone(first['carried_seed'])
        self.assertIsNotNone(second['carried_seed'])
        self.assertAlmostEqual(first['energy'], 1-gardening.PLANT_COST)
        self.assertEqual(second['energy'], 1.0)
        self.assertEqual(len(events), 1)

    def test_recording_cadence_preserves_world_and_final_frame(self):
        options = dict(agents=4, patches=12, gardening=True, soil_limits=True,
                       water=True, hazards=False, turn_sign=-1, turn_gain=1)
        dense = simulate_ecosystem('demo.json', 101, 4, record_every=1, **options)
        sparse = simulate_ecosystem('demo.json', 101, 4, record_every=6, **options)
        self.assertEqual(dense['events'], sparse['events'])
        self.assertEqual(dense['final'], sparse['final'])
        self.assertEqual(dense['roster'], sparse['roster'])
        self.assertEqual(dense['ticks'][-1], sparse['ticks'][-1])
        self.assertEqual(sparse, simulate_ecosystem('demo.json', 101, 4, record_every=6, **options))
