"""Deterministic input probes and controls for the experimental rate model."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
from sim import Circuit, simulate


def probe(graph, side):
    c = Circuit(graph)
    drives = [0.5 if n['role'] == 'sensory' and (side == 'both' or n['side'] == side) else 0.0 for n in c.nodes]
    for _ in range(200): c.step(drives)
    left, right = c.motors()
    return {'left_motor': left, 'right_motor': right, 'right_minus_left': right-left,
            'saturated_neurons': sum(a >= .999 for a in c.activity)}


def evaluate(path, ticks=500, seeds=10):
    if ticks < 1 or seeds < 1: raise ValueError('ticks and seeds must be positive')
    path = Path(path)
    graph = json.loads(path.read_text())
    result = {'graph_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'nodes':len(graph['nodes']), 'connections':len(graph['edges']),
              'retained_synapses':sum(e['weight'] for e in graph['edges']),
              'ticks_per_run':ticks, 'seed_count':seeds,
              'controller':{'model':'bounded rate model', 'sign_policy':'all excitatory (assumption)',
                            'edge_gain':'raw synapse count / 100', 'update':'clip(0.75*old + 0.25*(input + recurrent), 0, 1)',
                            'movement':'speed = 0.13*min(1,L+R); turn = clip(0.15*(R-L), -0.3, 0.3)',
                            'learning':False},
              'static_probes':{s:probe(graph,s) for s in ['left','right','both','none']}, 'controls':{}}
    for name in ['intact','disconnected','no_input','shuffled']:
        runs=[]
        for seed in range(seeds):
            angle=random.Random(seed).uniform(-math.pi,math.pi)
            initial_food=(6*math.cos(angle),6*math.sin(angle))
            trace=simulate(path,ticks,seed,initial_food=initial_food,drive_enabled=name!='no_input',
                           disconnected=name=='disconnected',shuffle_seed=seed if name=='shuffled' else None)
            points=[(0.,0.)]+[(t['x'],t['y']) for t in trace]
            runs.append({'seed':seed, 'initial_food':initial_food,
                         'food_collected':sum(t['ate'] for t in trace),
                         'distance_travelled':sum(math.dist(a,b) for a,b in zip(points,points[1:])),
                         'mean_motor_activity':statistics.mean(t['left_motor']+t['right_motor'] for t in trace),
                         'mean_saturated_fraction':statistics.mean(t['saturated_fraction'] for t in trace)})
        result['controls'][name]={'mean_food_collected':statistics.mean(r['food_collected'] for r in runs),
                                  'mean_distance_travelled':statistics.mean(r['distance_travelled'] for r in runs),
                                  'runs':runs}
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('graph'); p.add_argument('--ticks',type=int,default=500);p.add_argument('--seeds',type=int,default=10)
    p.add_argument('--out',default='experiment.json')
    a=p.parse_args()
    try:
        result=evaluate(a.graph,a.ticks,a.seeds)
        Path(a.out).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        print(json.dumps({k:{kk:vv for kk,vv in v.items() if kk!='runs'} for k,v in result['controls'].items()},indent=2))
    except (ValueError,OSError) as exc:p.exit(2,f'Error: {exc}\n')
