"""Synthetic checks for the GitHub Pages live ecosystem. Not MaleCNS validation."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'


class PagesTests(unittest.TestCase):
    def test_live_page_exposes_parameter_controls(self):
        html = (DOCS / 'index.html').read_text()
        for token in ('id="agents"', 'id="food-rate"', 'id="aging-rate"', 'id="repro-rate"',
          'id="mutation-rate"', 'id="randomize"', 'id="preset"', 'id="lineage-board"', 'malecns-derived'):
            self.assertIn(token, html)
        engine = (DOCS / 'engine.js').read_text()
        self.assertIn('function inheritGenome', engine)
        self.assertIn('relocatePatch', engine)
        self.assertIn('lifespanOf', engine)
        self.assertIn('function reproduce', engine)
        self.assertIn('createWorld', engine)
        circuit = DOCS / 'circuits' / 'dng13.json'
        self.assertTrue(circuit.exists())
        text = circuit.read_text()
        self.assertIn('MaleCNS', text)
        self.assertIn('official-file-derived-subgraph', text)


if __name__ == '__main__':
    unittest.main()
