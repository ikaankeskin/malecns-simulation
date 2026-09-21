"""Synthetic ablation runner checks, not validation on biological behaviour."""
import unittest
from pathlib import Path
from social_experiment import compare


class SocialExperimentTests(unittest.TestCase):
    def test_paired_runs_are_repeatable(self):
        graph = Path(__file__).resolve().parents[1] / 'demo.json'
        first = compare(graph, [0, 1], ticks=12)
        self.assertEqual(first, compare(graph, [0, 1], ticks=12))
        self.assertEqual(len(first['rows']), 4)
        self.assertTrue(all(r['social']['sent'] == 0 for r in first['rows'] if not r['communication']))
        with self.assertRaises(ValueError):
            compare(graph, [0, 0], ticks=12)

    def test_learning_ablation_keeps_communication_on(self):
        graph = Path(__file__).resolve().parents[1] / 'demo.json'
        result = compare(graph, [0, 1], ticks=12, learning=True)
        self.assertEqual(result['ablation'], 'social_learning')
        self.assertTrue(all(r['communication'] for r in result['rows']))
        self.assertEqual([r['social_learning'] for r in result['rows']], [False, True, False, True])
        self.assertEqual(result, compare(graph, [0, 1], ticks=12, learning=True))
