"""Large-map paired planting ablation. CPU only, no biological claim."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from ecosystem import simulate_ecosystem


def compare(graph, seeds, ticks=2000):
    seeds=list(seeds)
    if not seeds or len(set(seeds))!=len(seeds):
        raise ValueError('provide distinct seeds')
    rows=[]
    for seed in seeds:
        for enabled in (False,True):
            result=simulate_ecosystem(graph,ticks,seed,gardening=enabled,map_half=80,patches=96,
                agents=24,hazards=False,predation=False,gifts=False,lifetime_learning=False,
                turn_sign=-1,turn_gain=1,record_every=ticks)
            final=result['final']
            rows.append(dict(seed=seed,gardening=enabled,
                **{k:final[k] for k in ('alive','births','meals')},**result['gardens']))
    metrics=('alive','births','meals','planted','harvests','descendant_meals','posthumous_meals')
    return dict(ablation='gardening',graph=str(graph),graph_sha256=hashlib.sha256(Path(graph).read_bytes()).hexdigest(),
        ticks=ticks,seeds=seeds,rules=result['rules'],decoder=dict(turn_sign=-1,turn_gain=1),rows=rows,
        means={name:{k:mean(row[k] for row in rows if row['gardening']==enabled) for k in metrics}
               for name,enabled in [('off',False),('on',True)]},
        caveat='Exploratory paired seeds; only gardening changes. Same 160×160 world, 96 starting patches and 24 agents. '
        'Rules describe the on condition. This tests seed acquisition, planting cost and persistent extra food together. '
        'Additional plants use an implicit environmental resource supply, not a closed energy budget. '
        'Descendant and posthumous meals can overlap. No confidence intervals, soil depletion or biological claim. '
        'Python and browser RNGs differ.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph');parser.add_argument('--seeds',default='0,1,2,3,4')
    parser.add_argument('--ticks',type=int,default=2000);parser.add_argument('--out',default='garden-comparison.json')
    args=parser.parse_args()
    report=compare(args.graph,[int(s) for s in args.seeds.split(',')],args.ticks)
    Path(args.out).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report['means'],indent=2))
