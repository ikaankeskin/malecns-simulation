"""Synthetic garden lifecycle and Python/browser agreement checks."""
import copy
import json
import random
import subprocess
import unittest
from pathlib import Path
import gardening as G
from ecosystem import advance_patch, rules_from, simulate_ecosystem

ROOT = Path(__file__).resolve().parents[1]


class GardeningTests(unittest.TestCase):
    def scene(self):
        return ([dict(id=0, x=0, y=0, energy=1, alive=True, generation=0)],
                [dict(id=0,x=0,y=0,stage='mature',nutrition=1)],
                rules_from(dict(gardening=True,map_half=80)))

    def test_cost_distance_inventory_and_fixed_regrowth(self):
        agents, patches, rules = self.scene()
        a=agents[0]
        G.on_meal(a,patches[0],agents,0,rules)
        seed=copy.deepcopy(a['carried_seed'])
        G.on_meal(a,patches[0],agents,1,rules)
        self.assertEqual(a['carried_seed'],seed)
        G.plant_seeds(agents,patches,20,rules,[])
        self.assertEqual(len(patches),1)
        a['x']=4
        a['energy']=.79
        G.plant_seeds(agents,patches,20,rules,[])
        self.assertEqual(len(patches),1)
        a['energy']=1
        G.plant_seeds(agents,patches,20,rules,[])
        self.assertAlmostEqual(a['energy'],.92)
        self.assertIsNone(a['carried_seed'])
        garden=patches[-1]
        self.assertEqual(garden['planter'],0)
        garden.update(stage='cooldown',timer=1)
        advance_patch(garden,rules,random.Random(0))
        self.assertEqual((garden['x'],garden['y']),(4,0))
        self.assertEqual(garden['stage'],'seed')

    def test_descendant_and_posthumous_meals(self):
        agents,patches,rules=self.scene()
        G.on_meal(agents[0],patches[0],agents,0,rules)
        agents[0]['x']=4
        G.plant_seeds(agents,patches,20,rules,[])
        agents[0]['alive']=False
        child=dict(id=1,parents=[0,2],alive=True)
        grandchild=dict(id=3,parents=[1,4],alive=True)
        agents.extend([child,grandchild])
        for t in range(10): G.on_meal(grandchild,patches[-1],agents,100+t,rules)
        self.assertEqual(patches[-1]['descendant_meals'],10)
        self.assertEqual(patches[-1]['posthumous_meals'],10)
        self.assertEqual(len(patches[-1]['recent_eaters']),6)
        self.assertEqual(grandchild['carried_seed']['plant_generation'],2)

    def test_expiry_disabled_and_capacity(self):
        agents,patches,rules=self.scene()
        G.on_meal(agents[0],patches[0],agents,0,dict(rules,gardening=False))
        self.assertNotIn('carried_seed',agents[0])
        G.on_meal(agents[0],patches[0],agents,0,rules)
        agents[0]['x']=4
        G.plant_seeds(agents,patches,600,rules,[])
        self.assertIsNone(agents[0]['carried_seed'])
        G.on_meal(agents[0],patches[0],agents,601,rules)
        patches.extend(dict(id=i+1,x=-20,y=-20,planter=0) for i in range(64))
        G.plant_seeds(agents,patches,630,rules,[])
        self.assertEqual(len(patches),65)

    def test_cross_engine_fixture(self):
        agents,patches,rules=self.scene()
        fixture=json.dumps([agents,patches,rules])
        G.on_meal(agents[0],patches[0],agents,0,rules)
        agents[0]['x']=4
        G.plant_seeds(agents,patches,20,rules,[])
        code="""require('./docs/gardening.js'); const G=globalThis.MaleCNSGardening;
const [a,p,r]=JSON.parse(process.argv[1]);G.onMeal(a[0],p[0],a,0,r);a[0].x=4;
G.plantSeeds(a,p,20,r,[]);console.log(JSON.stringify([a,p]));"""
        result=subprocess.run(['node','-e',code,fixture],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),[agents,patches])

    def test_large_world_repeatability_and_snapshot_independence(self):
        kwargs=dict(gardening=True,map_half=80,patches=96,hazards=False,turn_sign=-1,turn_gain=1,record_every=100)
        first=simulate_ecosystem(ROOT/'circuits/dng13.json',400,4,**kwargs)
        self.assertEqual(first,simulate_ecosystem(ROOT/'circuits/dng13.json',400,4,**kwargs))
        for frame in first['ticks']:
            self.assertTrue(all(abs(p['x'])<=80 and abs(p['y'])<=80 for p in frame['patches']))
        self.assertIsNot(first['ticks'][0]['patches'][0],first['ticks'][-1]['patches'][0])
