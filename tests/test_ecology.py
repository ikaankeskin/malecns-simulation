"""Synthetic ecology fixtures; not biological validation of MaleCNS."""
import copy
import json
import shutil
import subprocess
import unittest
from pathlib import Path
from ecosystem import (rules_from, season_at, scavenge_corpses, compost_corpse,
                       advance_patch, simulate_ecosystem)

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return [dict(id=9, alive=False, x=0, y=0, energy=0, death_tick=0, corpse_until=180),
            dict(id=2, alive=True, x=.1, y=0, energy=.5, meals=0, ate=False),
            dict(id=1, alive=True, x=-.1, y=0, energy=.5, meals=0, ate=False)]


class EcologyTests(unittest.TestCase):
    def test_seasons_and_growth(self):
        rules = rules_from({'season_length': 10})
        self.assertEqual([season_at(t, rules)['name'] for t in (0, 10, 20, 30, 40)],
                         ['Bloom', 'Abundance', 'Drought', 'Recovery', 'Bloom'])
        fast = dict(stage='growing', timer=1)
        slow = copy.deepcopy(fast)
        advance_patch(fast, rules, growth=1.65)
        advance_patch(slow, rules, growth=.3)
        self.assertEqual(fast['stage'], 'mature')
        self.assertEqual(slow['stage'], 'growing')
        self.assertEqual(season_at(100, rules_from({'seasons': False}))['growth'], 1)

    def test_single_meal_and_freshness(self):
        agents, events, rules = fixture(), [], rules_from({})
        self.assertEqual(scavenge_corpses(agents, 90, rules, events), 1)
        self.assertEqual(events[0]['agent'], 1)  # distance tie resolves by ID
        self.assertAlmostEqual(agents[2]['energy'], .675)
        self.assertEqual(agents[2]['meals'], 0)  # no lifespan bonus
        self.assertIsNone(agents[0]['corpse_until'])
        self.assertEqual(scavenge_corpses(agents, 91, rules, events), 0)

    def test_ineligible_meals(self):
        for tick in (0, 180, 181):
            self.assertEqual(scavenge_corpses(fixture(), tick, rules_from({}), []), 0)
        for field, value in [('ate', True), ('energy', 1.1)]:
            agents = fixture()
            for a in agents[1:]:
                a[field] = value
            self.assertEqual(scavenge_corpses(agents, 1, rules_from({}), []), 0)
        self.assertEqual(scavenge_corpses(fixture(), 1, rules_from({'scavenging': False}), []), 0)

    def test_compost_nearest_immature_patch_only(self):
        patches = [dict(id=0, x=0, y=0, stage='mature', timer=0),
                   dict(id=1, x=1, y=0, stage='growing', timer=8),
                   dict(id=2, x=2, y=0, stage='seed', timer=20)]
        events = []
        self.assertTrue(compost_corpse(fixture()[0], patches, 180, rules_from({}), events))
        self.assertEqual([p['timer'] for p in patches], [0, 0, 20])
        self.assertEqual(events[0]['patch'], 1)
        self.assertFalse(compost_corpse(dict(id=9, x=100, y=100), patches, 180, rules_from({}), []))

    def test_replay_determinism_and_bounds(self):
        kwargs = dict(agents=4, repro_rate=0, season_length=20, map_half=4)
        first = simulate_ecosystem(ROOT / 'demo.json', 220, 4, **kwargs)
        self.assertEqual(first, simulate_ecosystem(ROOT / 'demo.json', 220, 4, **kwargs))
        self.assertTrue(all(abs(a['x']) <= 4 and abs(a['y']) <= 4
                            for frame in first['ticks'] for a in frame['agents']))
        self.assertTrue(any(e['kind'] == 'season' for e in first['events']))

    @unittest.skipUnless(shutil.which('node'), 'Node required for cross-engine fixture')
    def test_browser_matches_ecology_fixture(self):
        code = r"""
        const assert = require('node:assert/strict');
        require('./docs/engine.js');
        const E = globalThis.MaleCNSEco, rules = E.rulesFrom({});
        const original = JSON.parse(process.argv[1]);
        for (const tick of [0, 180, 181]) assert.equal(E.scavengeCorpses(structuredClone(original),tick,rules,[]),0);
        const agents = structuredClone(original), events=[];
        assert.equal(E.scavengeCorpses(agents,90,rules,events),1);
        assert.equal(E.scavengeCorpses(agents,91,rules,events),0);
        assert.equal(E.scavengeCorpses(structuredClone(original),90,{...rules,scavenging:false},[]),0);
        const patches=[{id:0,x:1,y:0,stage:'growing',timer:8},{id:1,x:2,y:0,stage:'seed',timer:20}];
        assert.equal(E.compostCorpse(original[0],patches,180,rules,[]),true);
        assert.deepEqual(patches.map(p=>p.timer),[0,20]);
        const fast={stage:'growing',timer:1},slow={...fast};
        E.advancePatch(fast,rules,null,1.65); E.advancePatch(slow,rules,null,.3);
        assert.equal(fast.stage,'mature'); assert.equal(slow.stage,'growing');
        console.log(JSON.stringify({agents,season:E.seasonAt(800,rules)}));
        """
        result = subprocess.run(['node', '-e', code, json.dumps(fixture())], cwd=ROOT,
                                capture_output=True, text=True, check=True)
        actual = json.loads(result.stdout)
        expected = fixture()
        scavenge_corpses(expected, 90, rules_from({}), [])
        self.assertEqual(actual, dict(agents=expected, season=season_at(800, rules_from({}))))
