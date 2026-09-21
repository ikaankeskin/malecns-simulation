"""Synthetic ecology-ablation checks, not validation on biological behaviour."""
import unittest
from pathlib import Path
from ecology_experiment import compare


class EcologyExperimentTests(unittest.TestCase):
    def test_paired_runs_are_repeatable(self):
        graph = Path(__file__).resolve().parents[1] / 'demo.json'
        first = compare(graph, [0, 1], ticks=12)
        self.assertEqual(first, compare(graph, [0, 1], ticks=12))
        self.assertEqual(len(first['rows']), 8)
        self.assertTrue(all(row['scavenged'] == 0 for row in first['rows'] if not row['scavenging']))
        self.assertNotIn('seasons', first['rules'])
        self.assertIn('compost_boost', first['rules'])
        with self.assertRaises(ValueError):
            compare(graph, [0, 0], ticks=12)
