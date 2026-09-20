"""Synthetic-only tests for ecosystem v0.1. Not MaleCNS validation."""
import unittest
from pathlib import Path
from ecosystem import claim_patches, simulate_ecosystem
from view import ecosystem_document, render_viewer

DEMO = Path(__file__).resolve().parents[1] / 'demo.json'


class EcosystemTests(unittest.TestCase):
    def test_only_mature_patches_can_be_claimed(self):
        agents = [{'id': 0, 'x': 0.0, 'y': 0.0, 'alive': True}]
        patches = [
            {'id': 0, 'x': 0.0, 'y': 0.0, 'stage': 'growing'},
            {'id': 1, 'x': 0.1, 'y': 0.0, 'stage': 'mature'},
        ]
        self.assertEqual(claim_patches(agents, patches, 0.4)[0], {1: 0})

    def test_patches_regrow_after_being_eaten(self):
        from ecosystem import advance_patch, rules_from
        rules = rules_from({'cooldown_ticks': 2, 'seed_ticks': 1, 'grow_ticks': 2, 'agents': 1, 'patches': 1})
        patch = {'id': 0, 'x': 0.0, 'y': 0.0, 'stage': 'cooldown', 'timer': 2, 'nutrition': 1.0, 'consumed_by': 0}
        seen = []
        for _ in range(8):
            advance_patch(patch, rules)
            seen.append(patch['stage'])
        self.assertEqual(seen[1], 'seed')
        self.assertIn('growing', seen)
        self.assertIn('mature', seen)
        result = simulate_ecosystem(DEMO, 80, 4, agents=2, patches=2, map_half=8, eat_radius=40,
                                    turn_sign=-1, turn_gain=1, cooldown_ticks=5, grow_ticks=5, seed_ticks=2)
        self.assertGreater(result['final']['meals'], 0)
        self.assertTrue(any(event['kind'] == 'food_mature' for event in result['events']))

    def test_starvation_and_old_age_are_labelled(self):
        starved = simulate_ecosystem(DEMO, 40, 1, agents=2, patches=1, map_half=12, disconnected=True,
                                     base_drain=0.2, move_cost=0.0, max_age=1000)
        self.assertTrue(any(event.get('cause') == 'starvation' for event in starved['events']))
        aged = simulate_ecosystem(DEMO, 20, 1, agents=2, patches=1, map_half=12, disconnected=True,
                                  max_age=5, base_drain=0.0001, corpse_ticks=3, meal_life=0)
        self.assertTrue(any(event.get('cause') == 'old_age' for event in aged['events']))
        self.assertTrue(any(frame['corpses'] for frame in aged['ticks']))
        last = aged['ticks'][-1]
        self.assertEqual(last['corpses'], [])

    def test_ecosystem_is_deterministic_and_html_is_synthetic(self):
        a = simulate_ecosystem(DEMO, 60, 3, agents=4, patches=3, map_half=12, turn_sign=-1, turn_gain=1)
        b = simulate_ecosystem(DEMO, 60, 3, agents=4, patches=3, map_half=12, turn_sign=-1, turn_gain=1)
        self.assertEqual(a['final'], b['final'])
        self.assertEqual(a['ticks'][-1], b['ticks'][-1])
        payload = ecosystem_document(DEMO, 25, 2, agents=3, patches=2, map_half=10, turn_sign=-1, turn_gain=1)
        self.assertEqual(payload['kind'], 'synthetic')
        self.assertEqual(payload['mode'], 'ecosystem')
        html = render_viewer(payload)
        self.assertIn('eco-wrap', html)
        self.assertIn('Reproduction is a proximity rule', html)

    def test_offspring_blend_and_mutate_simulation_parameters(self):
        import random
        from ecosystem import BASE_GENOME, inherit_genome
        mid, mutations = inherit_genome(
            {'turn_gain': 1.0, 'sensory_gain': 1.2, 'metabolism': 0.8, 'speed': 1.0},
            {'turn_gain': 1.4, 'sensory_gain': 1.0, 'metabolism': 1.0, 'speed': 1.2},
            random.Random(0), {'mutation_rate': 0.0, 'mutation_sigma': 0.1})
        self.assertAlmostEqual(mid['turn_gain'], 1.2)
        self.assertAlmostEqual(mid['speed'], 1.1)
        self.assertEqual(mutations, {})
        changed, deltas = inherit_genome(
            dict(BASE_GENOME), dict(BASE_GENOME),
            random.Random(3), {'mutation_rate': 1.0, 'mutation_sigma': 0.25})
        self.assertTrue(deltas)
        self.assertTrue(any(abs(changed[gene] - 1.0) > 1e-6 for gene in BASE_GENOME))
        born = simulate_ecosystem(
            DEMO, 12, 1, agents=4, patches=1, map_half=8, disconnected=True,
            min_repro_age=1, min_repro_energy=0.2, mate_radius=40, repro_cooldown=3,
            repro_cost=0.05, max_age=500, base_drain=0.0001, move_cost=0.0,
            max_population=8, energy_start=1.0, mutation_rate=1.0, mutation_sigma=0.2)
        child = next(agent for agent in born['ticks'][-1]['agents'] if agent['generation'] > 0)
        self.assertEqual(set(child['genome']), set(BASE_GENOME))
        self.assertTrue(any(event.get('mutations') for event in born['events'] if event['kind'] == 'born'))
        clone = simulate_ecosystem(
            DEMO, 12, 1, agents=4, patches=1, map_half=8, disconnected=True,
            min_repro_age=1, min_repro_energy=0.2, mate_radius=40, repro_cooldown=3,
            repro_cost=0.05, max_age=500, base_drain=0.0001, move_cost=0.0,
            max_population=8, mutation_rate=0.0)
        frozen = next(agent for agent in clone['ticks'][-1]['agents'] if agent['generation'] > 0)
        self.assertEqual(frozen['genome']['speed'], 1.0)
        self.assertEqual(frozen['mutations'], {})

    def test_nearby_agents_can_reproduce_and_respect_the_cap(self):
        born = simulate_ecosystem(
            DEMO, 12, 1, agents=4, patches=1, map_half=8, disconnected=True,
            min_repro_age=1, min_repro_energy=0.2, mate_radius=40, repro_cooldown=3,
            repro_cost=0.05, max_age=500, base_drain=0.0001, move_cost=0.0,
            max_population=6, energy_start=1.0, repro_rate=1.0)
        self.assertGreater(born['final']['births'], 0)
        self.assertLessEqual(born['final']['peak'], 6)
        self.assertTrue(any(event['kind'] == 'born' for event in born['events']))
        child = next(agent for agent in born['ticks'][-1]['agents'] if agent['generation'] > 0)
        self.assertEqual(len(child['parents']), 2)
        off = simulate_ecosystem(
            DEMO, 20, 1, agents=4, patches=1, map_half=8, disconnected=True,
            min_repro_age=1, min_repro_energy=0.2, mate_radius=40, repro_rate=0,
            max_age=500, base_drain=0.0001)
        self.assertEqual(off['final']['births'], 0)

    def test_food_and_aging_rates_change_derived_timers(self):
        from ecosystem import rules_from
        fast = rules_from({'food_rate': 2.0, 'aging_rate': 2.0, 'repro_rate': 2.0})
        slow = rules_from({'food_rate': 0.5, 'aging_rate': 0.5, 'repro_rate': 0.5})
        self.assertLess(fast['grow_ticks'], slow['grow_ticks'])
        self.assertLess(fast['max_age'], slow['max_age'])
        self.assertLess(fast['repro_cooldown'], slow['repro_cooldown'])

    def test_food_relocates_and_meals_extend_life(self):
        import random
        from ecosystem import relocate_patch, rules_from, litter_size
        patch = {'x': 0.0, 'y': 0.0}
        relocate_patch(patch, random.Random(2), {'map_half': 20.0})
        self.assertNotEqual((patch['x'], patch['y']), (0.0, 0.0))
        self.assertEqual(litter_size({'fertility': 1.0}), 1)
        self.assertEqual(litter_size({'fertility': 1.4}), 2)
        fed = simulate_ecosystem(DEMO, 16, 1, agents=2, patches=1, map_half=8, disconnected=True,
                                 eat_radius=40, max_age=6, meal_life=40, meal_life_cap=80,
                                 base_drain=0.0001, move_cost=0.0, repro_rate=0)
        self.assertGreater(fed['ticks'][-1]['alive'], 0)
        two = [{'id': 0, 'x': 0.0, 'y': 0.0, 'alive': True, 'contested': 0, 'displaced': 0},
               {'id': 1, 'x': 0.05, 'y': 0.0, 'alive': True, 'contested': 0, 'displaced': 0}]
        claimed, contests = claim_patches(two, [{'id': 0, 'x': 0.0, 'y': 0.0, 'stage': 'mature'}], 0.4)
        self.assertEqual(claimed, {0: 0})
        self.assertEqual(len(contests), 1)
        self.assertEqual(two[0]['contested'], 1)
        self.assertEqual(two[1]['displaced'], 1)


if __name__ == '__main__':
    unittest.main()
