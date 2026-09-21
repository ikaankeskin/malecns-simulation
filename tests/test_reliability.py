"""Synthetic sender-reliability checks; not biological validation."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import unittest
import social
from ecosystem import rules_from

ROOT = Path(__file__).resolve().parents[1]


class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.rules = rules_from({})
        self.agent = dict(id=2, genome=dict(responsiveness=.5))
        social.initialize(self.agent)

    def test_neutral_prior_and_direction(self):
        self.assertEqual(social.reliability(self.agent, 1, 0, self.rules), .5)
        self.assertAlmostEqual(social.learn_outcome(self.agent, 1, 0, 'meals', self.rules), 2/3)
        self.assertAlmostEqual(social.learn_outcome(self.agent, 3, 0, 'empty', self.rules), 1/3)
        self.assertEqual(social.reliability(self.agent, 9, 0, self.rules), .5)

    def test_decay_is_read_only_and_returns_to_neutral(self):
        social.learn_outcome(self.agent, 1, 0, 'meals', self.rules)
        saved = copy.deepcopy(self.agent)
        self.assertAlmostEqual(social.reliability(self.agent, 1, 400, self.rules), .6)
        self.assertAlmostEqual(social.reliability(self.agent, 1, 40000, self.rules), .5)
        self.assertEqual(saved, self.agent)

    def test_bounded_evidence_and_deterministic_eviction(self):
        for _ in range(100):
            social.learn_outcome(self.agent, 1, 0, 'meals', self.rules)
        self.assertLessEqual(self.agent['relationships'][0]['useful'], 16)
        for source in range(2, 10):
            social.learn_outcome(self.agent, source, 1, 'empty', self.rules)
        self.assertEqual(len(self.agent['relationships']), 8)
        self.assertNotIn(1, [r['source'] for r in self.agent['relationships']])
        social.learn_outcome(self.agent, 10, 1, 'empty', self.rules)
        self.assertNotIn(2, [r['source'] for r in self.agent['relationships']])

    def test_no_learning_from_expiry_or_disabled_mode(self):
        self.assertIsNone(social.learn_outcome(self.agent, 1, 0, 'expired', self.rules))
        for flag in ('communication', 'social_learning'):
            rules = dict(self.rules, **{flag: False})
            self.assertIsNone(social.learn_outcome(self.agent, 1, 0, 'meals', rules))
        self.assertEqual(self.agent['relationships'], [])

    def test_scores_change_acceptance_not_genome(self):
        social.learn_outcome(self.agent, 1, 0, 'meals', self.rules)
        social.learn_outcome(self.agent, 3, 0, 'empty', self.rules)
        counts = []
        for source in (1, 3):
            multiplier = 2 * social.reliability(self.agent, source, 0, self.rules)
            counts.append(sum(social.willing(self.agent, t, 'responsiveness', multiplier) for t in range(1009)))
        self.assertGreater(counts[0], counts[1])
        self.assertEqual(self.agent['genome']['responsiveness'], .5)
        self.assertEqual(social.reliability(self.agent, 1, 0, dict(self.rules, social_learning=False)), .5)

    def test_independent_agents_and_validation(self):
        other = dict(id=3, genome={})
        social.initialize(other)
        social.learn_outcome(self.agent, 1, 0, 'meals', self.rules)
        self.assertEqual(other['relationships'], [])
        with self.assertRaises(ValueError):
            rules_from(dict(social_learning=1))

    @unittest.skipUnless(shutil.which('node'), 'Node required for parity fixture')
    def test_cross_engine_learning_decay_and_disabled_feedback(self):
        code = """
        require('./docs/social.js');const S=globalThis.MaleCNSSocial;
        const a={id:2,genome:{responsiveness:.5}},rules={...S.DEFAULTS};S.initialize(a);
        S.learnOutcome(a,1,0,'meals',rules);S.learnOutcome(a,3,0,'empty',rules);
        S.learnOutcome(a,1,400,'empty',rules);S.learnOutcome(a,3,400,'expired',rules);
        S.learnOutcome(a,9,400,'meals',{...rules,social_learning:false});
        console.log(JSON.stringify({agent:a,view:S.relationshipView(a,800)}));
        """
        result = subprocess.run(['node','-e',code],cwd=ROOT,text=True,capture_output=True,check=True)
        for source, tick, outcome in [(1,0,'meals'),(3,0,'empty'),(1,400,'empty'),(3,400,'expired')]:
            social.learn_outcome(self.agent,source,tick,outcome,self.rules)
        self.assertEqual(json.loads(result.stdout),dict(agent=self.agent,view=social.relationship_view(self.agent,800)))
