"""Synthetic-only tests for decoder selection. Not MaleCNS validation."""
import json
import tempfile
import unittest
from pathlib import Path
from experiments import BASELINE_DECODER, candidate_decoders, decoder_experiment, select_decoder

DEMO = Path(__file__).resolve().parents[1] / 'demo.json'


class DecoderExperimentTests(unittest.TestCase):
    def test_candidate_grid_is_complete_and_includes_baseline(self):
        names = [decoder['name'] for decoder in candidate_decoders()]
        self.assertEqual(len(names), 12)
        self.assertEqual(len(set(names)), 12)
        self.assertIn(BASELINE_DECODER['name'], names)

    def test_selection_prefers_food_then_closer_approach(self):
        low = {'decoder': {'name': 'a'}, 'mean_food_collected': 0, 'mean_min_distance_to_first_food': 1,
               'mean_saturated_fraction': 0}
        high = {'decoder': {'name': 'b'}, 'mean_food_collected': 2, 'mean_min_distance_to_first_food': 5,
                'mean_saturated_fraction': 0}
        closer = {'decoder': {'name': 'c'}, 'mean_food_collected': 2, 'mean_min_distance_to_first_food': 0.5,
                  'mean_saturated_fraction': 0}
        saturated = {'decoder': {'name': 'd'}, 'mean_food_collected': 9, 'mean_min_distance_to_first_food': 0.1,
                     'mean_saturated_fraction': 0.9}
        self.assertEqual(select_decoder([low, high])['decoder']['name'], 'b')
        self.assertEqual(select_decoder([high, closer])['decoder']['name'], 'c')
        self.assertEqual(select_decoder([saturated, closer])['decoder']['name'], 'c')
        self.assertFalse(select_decoder([saturated])['eligible'])

    def test_synthetic_sweep_uses_disjoint_seeds_and_is_repeatable(self):
        first = decoder_experiment(DEMO, ticks=40, development_seeds=2, held_out_seeds=2)
        second = decoder_experiment(DEMO, ticks=40, development_seeds=2, held_out_seeds=2)
        self.assertEqual(first['development_seeds'], [0, 1])
        self.assertEqual(first['held_out_seeds'], [2, 3])
        self.assertTrue(set(first['development_seeds']).isdisjoint(first['held_out_seeds']))
        self.assertEqual(first['selection'], second['selection'])
        self.assertEqual(first['held_out']['intact_selected']['mean_food_collected'],
                         second['held_out']['intact_selected']['mean_food_collected'])
        self.assertEqual(first['held_out']['disconnected_selected']['mean_distance_travelled'], 0)
        self.assertEqual(first['held_out']['no_input_selected']['mean_distance_travelled'], 0)

    def test_report_is_json_serializable(self):
        result = decoder_experiment(DEMO, ticks=20, development_seeds=1, held_out_seeds=1)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.json'
            path.write_text(json.dumps(result, indent=2, allow_nan=False))
            loaded = json.loads(path.read_text())
        self.assertEqual(loaded['selection']['decoder']['name'], result['selection']['decoder']['name'])


if __name__ == '__main__':
    unittest.main()
