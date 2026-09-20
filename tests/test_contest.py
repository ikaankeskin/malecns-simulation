"""Synthetic-only tests for the scarce-food contest. Not MaleCNS validation."""
import unittest
from pathlib import Path
from contest import claim_meals, contest_rank, simulate_contest
from view import contest_document, render_viewer

DEMO = Path(__file__).resolve().parents[1] / 'demo.json'


class ContestTests(unittest.TestCase):
    def test_lowest_id_wins_a_shared_pellet(self):
        agents = [
            {'id': 2, 'x': 0.1, 'y': 0.0, 'alive': True},
            {'id': 0, 'x': 0.0, 'y': 0.1, 'alive': True},
            {'id': 1, 'x': 5.0, 'y': 5.0, 'alive': True},
        ]
        claimed = claim_meals(agents, [(0.0, 0.0)])
        self.assertEqual(claimed, {0: 0})

    def test_synthetic_contest_has_independent_state_and_no_respawn(self):
        result = simulate_contest(DEMO, 80, 4, agents=10, foods=3, map_half=20, turn_sign=-1, turn_gain=1)
        self.assertEqual(len(result['ticks']), 80)
        self.assertEqual(len(result['ticks'][0]['agents']), 10)
        self.assertEqual(len(result['ticks'][0]['foods']), 3)
        poses = [(round(agent['x'], 5), round(agent['y'], 5)) for agent in result['ticks'][0]['agents']]
        self.assertEqual(len(set(poses)), 10)
        food_counts = [len(tick['foods']) for tick in result['ticks']]
        self.assertEqual(food_counts, sorted(food_counts, reverse=True))
        self.assertLessEqual(food_counts[-1], food_counts[0])
        meals = [agent['meals'] for agent in result['ranking']]
        self.assertLessEqual(sum(meals), 3)
        first = result['ticks'][0]['agents']
        later = result['ticks'][20]['agents']
        self.assertTrue(any(a['x'] != b['x'] or a['y'] != b['y'] for a, b in zip(first, later)))

    def test_contest_is_deterministic_and_disconnected_flies_starve(self):
        a = simulate_contest(DEMO, 50, 7, agents=4, foods=2, map_half=12, turn_sign=-1, turn_gain=1)
        b = simulate_contest(DEMO, 50, 7, agents=4, foods=2, map_half=12, turn_sign=-1, turn_gain=1)
        self.assertEqual(a['winner'], b['winner'])
        self.assertEqual(a['ticks'][-1], b['ticks'][-1])
        dead = simulate_contest(DEMO, 30, 1, agents=3, foods=1, map_half=12, disconnected=True)
        last = dead['ticks'][-1]
        self.assertTrue(all(agent['x'] == last['agents'][i]['x'] for i, agent in enumerate(last['agents'])))
        start = dead['ticks'][0]['agents']
        self.assertTrue(all(agent['x'] == start[i]['x'] and agent['y'] == start[i]['y']
                            for i, agent in enumerate(last['agents'])))

    def test_rank_prefers_meals_then_energy(self):
        fed = {'id': 1, 'alive': True, 'meals': 1, 'energy': 0.2, 'death_tick': None}
        hungry = {'id': 0, 'alive': True, 'meals': 0, 'energy': 0.9, 'death_tick': None}
        self.assertGreater(contest_rank(fed), contest_rank(hungry))

    def test_contest_html_is_labelled_synthetic(self):
        payload = contest_document(DEMO, 12, 4, agents=5, foods=2, map_half=12, turn_sign=-1, turn_gain=1)
        self.assertEqual(payload['kind'], 'synthetic')
        self.assertEqual(payload['mode'], 'contest')
        html = render_viewer(payload)
        self.assertIn('data-fly', html)
        self.assertIn('Winner fly', html)


if __name__ == '__main__':
    unittest.main()
