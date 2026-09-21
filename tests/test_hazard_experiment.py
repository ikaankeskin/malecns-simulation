"""Synthetic hazard-ablation checks, not validation on biological behaviour."""
import unittest
from pathlib import Path
from hazard_experiment import compare


class HazardExperimentTests(unittest.TestCase):
    def test_paired_runs_are_repeatable(self):
        graph = Path(__file__).resolve().parents[1] / 'demo.json'
        first = compare(graph, [0, 1], ticks=8)
        self.assertEqual(first, compare(graph, [0, 1], ticks=8))
        self.assertEqual(len(first['rows']), 4)
        self.assertEqual([row['hazards'] for row in first['rows']], [False, True, False, True])
        self.assertNotIn('hazards', first['rules'])
        with self.assertRaises(ValueError):
            compare(graph, [0, 0], ticks=8)
