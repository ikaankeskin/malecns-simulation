"""Synthetic communication fixtures. Not biological or social intelligence validation."""
import copy
import json
import shutil
import subprocess
import unittest
from pathlib import Path
import social
from ecosystem import rules_from, simulate_ecosystem

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    agents = [dict(id=0,x=0,y=0,alive=True,energy=1,genome=dict(signalling=1,responsiveness=0)),
              dict(id=1,x=-3,y=0,alive=True,energy=1,genome=dict(signalling=0,responsiveness=1))]
    patches = [dict(id=0,x=3,y=0,stage='mature')]
    return agents, patches, [], [], rules_from(dict(sense_range=4))


class SocialTests(unittest.TestCase):
    def test_local_message_cost_cooldown_and_memory(self):
        agents, patches, signals, events, rules = fixture()
        social.begin_tick(agents,patches,signals,0,rules,events)
        self.assertEqual(len(signals),1)
        self.assertAlmostEqual(agents[0]['energy'],.99)
        self.assertEqual(len(agents[1]['memories']),1)
        target=social.select_target(agents[1],[],0,rules,events)
        self.assertEqual(target['kind'],'following_signal')
        agents[1]['target']=target
        social.begin_tick(agents,patches,signals,1,rules,events)
        self.assertEqual(social.totals(agents)['sent'],1)
        self.assertEqual(social.totals(agents)['received'],1)
        patches[0].update(x=50,stage='cooldown')
        self.assertEqual(agents[1]['memories'][0]['x'],3)  # no access to hidden relocation
        social.begin_tick(agents,patches,signals,24,rules,events)
        self.assertFalse(signals)
        self.assertTrue(agents[1]['memories'])
        social.begin_tick(agents,patches,signals,180,rules,events)
        self.assertFalse(agents[1]['memories'])
        self.assertEqual(agents[1]['social']['expired'],1)

    def test_arrival_success_and_empty_are_consumed_once(self):
        for success in (False, True):
            agents, patches, signals, events, rules=fixture()
            social.begin_tick(agents,patches,signals,0,rules,events)
            a=agents[1]
            a['target']=social.select_target(a,[],0,rules,events)
            a['x']=3
            # Once visible, the remembered goal stays attributable.
            a['target']=social.select_target(a,[dict(x=3,y=0,kind='foraging')],1,rules,events)
            a['meal_position']=dict(x=3,y=0) if success else None
            social.end_tick(agents,1,rules,events)
            social.end_tick(agents,1,rules,events)
            self.assertEqual(a['social']['meals' if success else 'empty'],1)
            self.assertFalse(a['memories'])
            self.assertEqual(a['energy'],1)  # no reward for communicating

    def test_range_death_energy_and_disabled(self):
        for mode in ('far','dead','poor','off','invisible'):
            agents,patches,signals,events,rules=fixture()
            if mode=='far': agents[1]['x']=-20
            if mode=='dead': agents[0]['alive']=False
            if mode=='poor': agents[0]['energy']=.1
            if mode=='off': rules['communication']=False
            if mode=='invisible': patches[0]['x']=20
            social.begin_tick(agents,patches,signals,0,rules,events)
            self.assertFalse(agents[1]['memories'])
            if mode!='far': self.assertFalse(signals)

    def test_memory_and_history_are_bounded(self):
        agents,patches,signals,events,rules=fixture()
        rules['signal_cooldown']=1
        for tick in range(20):
            patches[0]['x']=1+tick/100
            social.begin_tick(agents,patches,signals,tick,rules,events)
        self.assertLessEqual(len(agents[1]['memories']),4)
        for tick in range(10):
            social.remember_event(agents[1],tick,'empty',dict(source=0,x=0,y=0),events)
        self.assertEqual(len(agents[1]['social_history']),6)

    def test_determinism_and_independent_snapshots(self):
        opts=dict(agents=4,repro_rate=0,turn_sign=-1,turn_gain=1)
        first=simulate_ecosystem(ROOT/'demo.json',200,4,**opts)
        self.assertEqual(first,simulate_ecosystem(ROOT/'demo.json',200,4,**opts))
        frames=first['ticks']
        self.assertEqual(frames[0]['social']['sent'],sum(a['social']['sent'] for a in frames[0]['agents']))
        self.assertTrue(all(len(a['memories'])<=4 for f in frames for a in f['agents']))
        off=simulate_ecosystem(ROOT/'demo.json',200,4,communication=False,**opts)
        self.assertFalse(any(e['kind'].startswith('signal_') for e in off['events']))

    @unittest.skipUnless(shutil.which('node'),'Node required')
    def test_cross_engine_synthetic_fixture(self):
        agents,patches,signals,events,rules=fixture()
        payload=json.dumps(dict(agents=agents,patches=patches,rules=rules))
        code="""
        require('./docs/social.js');const S=globalThis.MaleCNSSocial;
        const {agents,patches,rules}=JSON.parse(process.argv[1]),signals=[],events=[];
        S.beginTick(agents,patches,signals,0,rules,events);
        agents[1].target=S.selectTarget(agents[1],[],0,rules,events);
        agents[1].x=3;agents[1].meal_position={x:3,y:0};
        S.endTick(agents,1,rules,events);
        console.log(JSON.stringify({agents,signals,events,totals:S.totals(agents)}));
        """
        result=subprocess.run(['node','-e',code,payload],cwd=ROOT,text=True,capture_output=True,check=True)
        social.begin_tick(agents,patches,signals,0,rules,events)
        agents[1]['target']=social.select_target(agents[1],[],0,rules,events)
        agents[1]['x']=3;agents[1]['meal_position']=dict(x=3,y=0)
        social.end_tick(agents,1,rules,events)
        self.assertEqual(json.loads(result.stdout),dict(agents=agents,signals=signals,events=events,totals=social.totals(agents)))
