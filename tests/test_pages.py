"""Synthetic checks for the GitHub Pages live ecosystem. Not MaleCNS validation."""
import unittest
import subprocess
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'


class PagesTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js is required for the browser-engine smoke test')
    def test_live_engine_loads_and_advances(self):
        code = """
        const assert = require('node:assert/strict');
        require('./docs/engine.js');
        const graph = require('./demo.json');
        const eco = globalThis.MaleCNSEco;
        const world = eco.createWorld(graph, {agents: 4, repro_rate: 0}, 4);
        for (let i = 0; i < 12; i++) eco.step(world);
        assert.equal(world.tick, 12);
        assert.equal(world.circuits.length, 4);
        assert.notEqual(world.circuits[0].activity, world.circuits[1].activity);
        assert.ok(world.agents.every(a => Number.isFinite(a.energy)));
        """
        completed = subprocess.run(['node', '-e', code], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(shutil.which('node'), 'Node.js required for page wiring test')
    def test_live_page_wiring(self):
        result = subprocess.run(['node', 'tests/live_page_smoke.cjs'], cwd=ROOT,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_live_page_exposes_parameter_controls(self):
        html = (DOCS / 'index.html').read_text()
        for token in ('id="agents"', 'id="food-rate"', 'id="aging-rate"', 'id="repro-rate"',
          'id="mutation-rate"', 'id="randomize"', 'id="preset"', 'id="lineage-board"',
          'id="family-tree"', 'id="hazards"', 'id="gifts-enabled"', 'id="predation-enabled"', 'id="sel-personality"', 'malecns-derived'):
            self.assertIn(token, html)
        engine = (DOCS / 'engine.js').read_text()
        self.assertIn('function inheritGenome', engine)
        self.assertIn('relocatePatch', engine)
        self.assertIn('lifespanOf', engine)
        self.assertIn('function reproduce', engine)
        self.assertIn('function familyTree', engine)
        self.assertIn('createWorld', engine)
        circuit = DOCS / 'circuits' / 'dng13.json'
        self.assertTrue(circuit.exists())
        text = circuit.read_text()
        self.assertIn('MaleCNS', text)
        self.assertIn('official-file-derived-subgraph', text)


if __name__ == '__main__':
    unittest.main()

