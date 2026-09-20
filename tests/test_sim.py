import copy
import json
from pathlib import Path
import tempfile
import unittest
from sim import Circuit, simulate, validate_decoder, validate_graph

DEMO = Path(__file__).resolve().parents[1]/'demo.json'

class SimulationTests(unittest.TestCase):
    def setUp(self): self.graph=json.loads(DEMO.read_text())

    def test_controls_stop_movement(self):
        for kwargs in [{'disconnected':True},{'drive_enabled':False}]:
            trace=simulate(DEMO,100,4,**kwargs)
            self.assertTrue(all(t['x']==t['y']==t['left_motor']==t['right_motor']==0 for t in trace))

    def test_input_changes_output_and_runs_repeat(self):
        c=Circuit(self.graph)
        for _ in range(50):c.step([.5,0,0,0,0,0])
        l,r=c.motors();self.assertGreater(r,0);self.assertEqual(l,0)
        self.assertEqual(simulate(DEMO,100,4),simulate(DEMO,100,4))

    def test_invalid_graphs_rejected(self):
        variants=[]
        g=copy.deepcopy(self.graph);g['nodes'].append(g['nodes'][0]);variants.append(g)
        g=copy.deepcopy(self.graph);g['edges'][0]['post']='absent';variants.append(g)
        for w in [-1,float('nan'),float('inf')]:
            g=copy.deepcopy(self.graph);g['edges'][0]['weight']=w;variants.append(g)
        for g in variants:
            with self.assertRaises(ValueError):validate_graph(g)

    def test_synapse_count_ratios_are_not_clipped(self):
        g=copy.deepcopy(self.graph);g['edges'][0]['weight']=250
        c=Circuit(g)
        self.assertEqual(c.incoming[2],[(0,2.5)])

    def test_invalid_ticks_rejected(self):
        with self.assertRaises(ValueError):simulate(DEMO,0,4)

    def test_invalid_decoder_rejected(self):
        for kwargs in [{'turn_sign': 0}, {'turn_sign': True}, {'sensory_sign': 2},
                       {'turn_gain': 0}, {'turn_gain': float('nan')}, {'speed_gain': -1}]:
            with self.assertRaises(ValueError):
                validate_decoder(**kwargs)

    def test_turn_sign_reverses_heading_on_synthetic_demo(self):
        attract = simulate(DEMO, 40, 4)
        avoid = simulate(DEMO, 40, 4, turn_sign=-1)
        self.assertGreater(attract[-1]['heading'], 0)
        self.assertLess(avoid[-1]['heading'], 0)
        self.assertNotEqual([t['heading'] for t in attract], [t['heading'] for t in avoid])

    def test_synthetic_demo_collects_food_with_default_decoder(self):
        trace = simulate(DEMO, 120, 4)
        self.assertGreaterEqual(sum(tick['ate'] for tick in trace), 1)

if __name__ == '__main__':unittest.main()
