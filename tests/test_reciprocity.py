"""Synthetic helper-memory and cross-engine checks, not biological validation."""
import copy
import json
import subprocess
import unittest
from pathlib import Path
from ecosystem import exchange_gifts, helper_view, remember_helper, rules_from


class ReciprocityTests(unittest.TestCase):
    def test_memory_decay_capacity_and_read_only_view(self):
        agent = {}
        remember_helper(agent, 1, 0, 0)
        self.assertEqual(helper_view(agent, 0), [])
        remember_helper(agent, 1, 2, 0)
        before = copy.deepcopy(agent)
        self.assertEqual(helper_view(agent, 400)[0]['energy'], 1)
        self.assertEqual(agent, before)
        remember_helper(agent, 1, 8, 400)
        self.assertEqual(helper_view(agent, 400)[0]['energy'], 4)
        for source in range(2, 11):
            remember_helper(agent, source, .1, 401)
        self.assertEqual(len(agent['helpers']), 8)
        self.assertEqual(agent['helpers'][0]['source'], 3)
        self.assertEqual(helper_view(agent, 1601), [])

    def test_recipient_preference_and_cross_engine_parity(self):
        agents = [dict(id=0, x=0, y=0, alive=True, energy=1),
                  dict(id=1, x=1, y=0, alive=True, energy=.1),
                  dict(id=2, x=1.1, y=0, alive=True, energy=.1)]
        remember_helper(agents[0], 2, .2, 0)
        for enabled, expected in [(False, 1), (True, 2)]:
            rules = rules_from(dict(gifts=True, reciprocity=enabled, gift_chance=1,
                                    lifetime_learning=False))
            bodies = copy.deepcopy(agents)
            events = []
            exchange_gifts(bodies, 1, rules, events)
            self.assertEqual(events[0]['recipient'], expected)
            self.assertAlmostEqual(sum(a['energy'] for a in bodies), 1.15)
            self.assertEqual(bodies[expected]['helpers'][0]['source'], 0)
            code = """
require('./docs/engine.js');
const e = globalThis.MaleCNSEco;
const [agents, rules] = JSON.parse(process.argv[1]);
const events = []; e.exchangeGifts(agents, 1, rules, events);
console.log(JSON.stringify({recipient: events[0].recipient, helpers: agents.map(a => e.helperView(a, 1)), energies: agents.map(a => a.energy)}));
"""
            result = subprocess.run(['node', '-e', code, json.dumps([agents, rules])],
                                    cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            actual = json.loads(result.stdout)
            self.assertEqual(actual['recipient'], expected)
            self.assertEqual(actual['helpers'], [helper_view(a, 1) for a in bodies])
            self.assertEqual(actual['energies'], [a['energy'] for a in bodies])

    def test_same_tick_gift_is_not_returned_help(self):
        agents = [dict(id=i, x=i, y=0, alive=True, energy=1) for i in range(2)]
        events = []
        exchange_gifts(agents, 0, rules_from(dict(gifts=True, reciprocity=True, gift_chance=1)), events)
        self.assertEqual(len(events), 2)
        self.assertFalse(any(e['returned_help'] for e in events))
        self.assertIsNot(agents[0]['helpers'], agents[1]['helpers'])
