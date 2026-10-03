"""Synthetic decision-boundary tests; not biological or model validation."""
import copy
from dataclasses import FrozenInstanceError, asdict
import json
import unittest
from unittest.mock import patch

from cognition.contracts import Decision, LEGACY_POLICY
from cognition.observation import prepare_targets
from ecosystem import rules_from, simulate_ecosystem
import social


def legacy_select(agent, direct, tick, rules, events):
    """Pre-adapter algorithm, retained as an independent behavioral oracle."""
    options = [p for p in direct if social.distance(agent, p) < rules['sense_range']]
    if rules['communication']:
        options = [dict(m, kind='following_signal') for m in agent.get('memories', [])] + options
    choice = min(options, key=lambda p: social.distance(agent, p), default=None)
    if choice and choice['kind'] == 'following_signal':
        memory = next(m for m in agent['memories'] if m['id'] == choice['id'])
        if not memory['followed']:
            memory['followed'] = True
            agent['social']['followed'] += 1
            social.remember_event(agent, tick, 'followed', memory, events)
    return choice


def observer():
    agent = dict(id=3, x=0., y=0., energy=1., age=7, heading=0.,
                 hidden_world={'future_rain': 10}, genome={'private': 123})
    social.initialize(agent)
    agent['memories'] = [dict(id='0:2', source=2, x=-2., y=0., tick=0,
                              until=20, followed=False, patch=99)]
    return agent


class CognitionTests(unittest.TestCase):
    def test_local_allowlist_and_immutable_owned_observation(self):
        agent = observer()
        visible = dict(x=1., y=0., kind='foraging', secret='unobserved metadata')
        direct = [dict(x=100., y=0., kind='foraging'), visible]
        context = prepare_targets(agent, direct, 7, 10, True)
        obs = context.observation
        payload = json.dumps(asdict(obs))
        for secret in ('hidden_world', 'future_rain', 'private', 'secret', 'patch', '100.0'):
            self.assertNotIn(secret, payload)
        self.assertEqual([c.evidence for c in obs.candidates], ['received_report', 'direct'])
        agent['memories'][0]['x'] = 50
        visible['x'] = 80
        self.assertEqual([c.x for c in obs.candidates], [-2., 1.])
        self.assertEqual(context.resolve(Decision(3, 7, 'target:1'))['x'], 1.)
        with self.assertRaises(FrozenInstanceError):
            obs.candidates[0].x = 3
        with self.assertRaises(FrozenInstanceError):
            obs.energy = 0

    def test_boundary_disabled_and_expired_reports(self):
        agent = observer()
        direct = [dict(x=10., y=0., kind='foraging')]
        self.assertEqual(prepare_targets(agent, direct, 7, 10, False).observation.candidates, ())
        self.assertEqual(prepare_targets(agent, [], 20, 10, True).observation.candidates, ())
        context = prepare_targets(agent, [], 7, 10, False)
        self.assertIsNone(context.resolve(LEGACY_POLICY.choose(context.observation)))

    def test_target_resolution_rejects_foreign_and_unknown_decisions(self):
        context = prepare_targets(observer(), [], 7, 10, True)
        for decision in (Decision(4, 7, 'target:0'), Decision(3, 8, 'target:0'),
                         Decision(3, 7, 'target:9'), {'candidate_id': 'target:0'}):
            with self.assertRaises(ValueError):
                context.resolve(decision)
        result = context.resolve(Decision(3, 7, 'target:0'))
        result['x'] = 99
        self.assertEqual(context.resolve(Decision(3, 7, 'target:0'))['x'], -2.)

    def test_memory_tie_and_follow_side_effects_match_original(self):
        rules = rules_from(dict(sense_range=10))
        agent = observer()
        old = copy.deepcopy(agent)
        events, old_events = [], []
        direct = [dict(x=2., y=0., kind='foraging')]
        for _ in range(2):
            self.assertEqual(social.select_target(agent, direct, 7, rules, events),
                             legacy_select(old, direct, 7, rules, old_events))
        self.assertEqual(agent, old)
        self.assertEqual(events, old_events)
        self.assertEqual(agent['social']['followed'], 1)
        context = prepare_targets(agent, [dict(x=1., y=0., kind='scavenging', id=8),
                                          dict(x=-1., y=0., kind='foraging')], 7, 10, False)
        self.assertEqual(context.resolve(LEGACY_POLICY.choose(context.observation))['id'], 8)

    def test_policy_receives_only_observation_and_controls_eligible_target(self):
        class LastPolicy:
            def choose(self, observation):
                return Decision(observation.agent_id, observation.tick,
                                observation.candidates[-1].id)
        agent = observer()
        chosen = social.select_target(agent, [dict(x=3., y=0., kind='foraging')], 7,
                                      rules_from(dict(sense_range=10)), [], policy=LastPolicy())
        self.assertEqual(chosen['kind'], 'foraging')
        self.assertEqual(agent['social']['followed'], 0)

    def test_complete_synthetic_trajectories_match_legacy(self):
        cases = [dict(), dict(communication=False), dict(drive_enabled=False),
                 dict(gardening=True, water=True, hazards=False),
                 dict(gifts=True, predation=True)]
        for seed, settings in enumerate(cases):
            with self.subTest(seed=seed, settings=settings):
                kwargs = dict(agents=4, patches=8, map_half=8, turn_sign=-1, turn_gain=1, **settings)
                current = simulate_ecosystem('demo.json', 180, seed, **kwargs)
                with patch('social.select_target', legacy_select):
                    previous = simulate_ecosystem('demo.json', 180, seed, **kwargs)
                self.assertEqual(current, previous)
