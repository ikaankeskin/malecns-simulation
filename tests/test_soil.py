"""Synthetic resource accounting and cross-engine checks, not biology."""
import copy
import json
import subprocess
import unittest
from pathlib import Path
import soil
from ecosystem import advance_patch, rules_from, compost_corpse

ROOT=Path(__file__).resolve().parents[1]


class SoilTests(unittest.TestCase):
    def scene(self):
        rules=rules_from(dict(soil_limits=True))
        s=soil.create(rules)
        patches=[dict(id=i,x=1+i,y=1,stage='growing',timer=rules['grow_ticks']) for i in range(2)]
        return rules,s,patches

    def test_shared_budget_fairness_and_conservation(self):
        rules,s,patches=self.scene()
        index=soil.cell_index(s,1,1);s['cells'][index]=.005
        reversed_patches=copy.deepcopy(patches[::-1]);other=copy.deepcopy(s)
        before=sum(s['cells'])
        rates=soil.growth_budget(s,patches,1.65,rules)
        self.assertEqual(rates,soil.growth_budget(other,reversed_patches,1.65,rules))
        self.assertAlmostEqual(rates[0],rates[1])
        self.assertLess(rates[0],1.65)
        self.assertAlmostEqual(sum(s['cells']),before+s['recovered']-s['consumed'])
        self.assertGreaterEqual(min(s['cells']),0)

    def test_recovery_cap_compost_and_no_timer_bypass(self):
        rules,s,patches=self.scene();index=soil.cell_index(s,1,1);s['cells'][index]=0
        for _ in range(1250):soil.growth_budget(s,[],1,rules)
        self.assertAlmostEqual(s['cells'][index],1)
        s['cells'][index]=.8;events=[];timer=patches[0]['timer']
        self.assertTrue(compost_corpse(dict(id=2,x=1,y=1),patches,0,rules,events,s))
        self.assertAlmostEqual(s['composted'],.2)
        self.assertEqual(patches[0]['timer'],timer)
        self.assertFalse(soil.compost(s,dict(id=2,x=1,y=1),1,events))

    def test_full_crop_cost_and_bounded_history(self):
        rules,s,patches=self.scene();p=patches[0]
        for t in range(200):
            rates=soil.growth_budget(s,[p],1.65,rules)
            advance_patch(p,rules,growth=rates.get(p['id'],1.65))
        self.assertEqual(p['stage'],'mature')
        self.assertAlmostEqual(p['soil_uptake'],soil.CROP_COST)
        for t in range(0,2000,100):soil.observe(s,[p],t)
        self.assertEqual(len(p['soil_history']),6)
        snapshot=soil.snapshot(s,[p]);s['cells'][0]=0
        self.assertEqual(snapshot['cells'][0],1)
        self.assertIsNone(soil.create(rules_from({})))
        self.assertEqual(soil.cell_index(s,20,20),s['n']**2-1)

    def test_python_javascript_parity(self):
        rules,s,patches=self.scene();s['cells'][soil.cell_index(s,1,1)]=.005
        fixture=json.dumps([rules,s,patches])
        rates=soil.growth_budget(s,patches,1.65,rules);soil.observe(s,patches,3)
        code="""require('./docs/soil.js');const S=globalThis.MaleCNSSoil;
const [r,s,p]=JSON.parse(process.argv[1]);const rates=S.growthBudget(s,p,1.65,r);S.observe(s,p,3);
console.log(JSON.stringify({rates,soil:s,patches:p}));"""
        out=subprocess.run(['node','-e',code,fixture],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(out.returncode,0,out.stderr)
        actual=json.loads(out.stdout)
        for k,v in rates.items():self.assertAlmostEqual(actual['rates'][str(k)],v)
        self.assertEqual(actual['patches'],patches)
        self.assertEqual(actual['soil'],s)
