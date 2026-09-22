"""Synthetic water accounting checks, not biological validation."""
import json
import subprocess
import unittest
import soil
import water
from ecosystem import rules_from, simulate_ecosystem


class WaterTests(unittest.TestCase):
    def test_conservation_bounds_and_parity(self):
        r=rules_from(dict(water=True, seasons=True, season_length=100))
        s=soil.create(r,4); initial=sum(s['water']['moisture'])
        fixture=json.dumps([r,s])
        patches=[dict(id=0,x=1,y=1,stage='growing',timer=100)]
        for t in range(800):
            soil.growth_budget(s,patches,1,r,t)
            if t==250:water.irrigate(s,0)
            self.assertGreaterEqual(min(s['water']['moisture']),-1e-12)
            self.assertLessEqual(max(s['water']['moisture']),1+1e-12)
        w=s['water']
        self.assertAlmostEqual(sum(w['moisture']),initial+w['rain']+w['river_input']+w['irrigated']-w['evaporated']-w['uptake'])
        self.assertAlmostEqual(s['consumed'],2*w['uptake'])
        code="""require('./docs/soil.js');const [r,s]=JSON.parse(process.argv[1]);
const p=[{id:0,x:1,y:1,stage:'growing',timer:100}];
for(let t=0;t<800;t++){MaleCNSSoil.growthBudget(s,p,1,r,t);if(t===250)MaleCNSWater.irrigate(s,0);}
console.log(JSON.stringify(s));"""
        out=subprocess.run(['node','-e',code,fixture],capture_output=True,text=True,check=True)
        actual=json.loads(out.stdout)
        for key in ('rain','river_input','evaporated','uptake','irrigated','reserve'):
            self.assertAlmostEqual(actual['water'][key],w[key])
        for a,b in zip(actual['water']['moisture'],w['moisture']):self.assertAlmostEqual(a,b)

    def test_empty_water_stops_crop_and_irrigation_is_finite(self):
        r=rules_from(dict(water=True,seasons=True,season_length=100))
        s=soil.create(r);w=s['water'];w['moisture']=[0]*len(w['moisture']);w['banks']=[0]*len(w['banks'])
        p=dict(id=1,x=1,y=1,stage='growing',timer=100)
        self.assertEqual(soil.growth_budget(s,[p],1,r,200)[1],0)
        self.assertEqual(s['consumed'],0)
        for _ in range(16):
            w['moisture'][0]=0;water.irrigate(s,0)
        self.assertEqual(w['reserve'],0);self.assertEqual(w['irrigated'],3)
        self.assertEqual(water.irrigate(s,-1),0)
        self.assertEqual(water.irrigate(None,0),0)

    def test_disabled_baseline_and_snapshot(self):
        self.assertEqual(simulate_ecosystem('demo.json',10,4),simulate_ecosystem('demo.json',10,4,water=False))
        r=rules_from(dict(water=True));self.assertTrue(r['soil_limits'])
        s=soil.create(r,4);snap=soil.snapshot(s,[]);s['water']['moisture'][0]=0
        self.assertGreater(snap['water']['moisture'][0],0)
