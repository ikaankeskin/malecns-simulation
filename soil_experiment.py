"""Paired soil limits ablation with planting enabled in both conditions."""
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
            result=simulate_ecosystem(graph,ticks,seed,gardening=True,soil_limits=enabled,
                map_half=80,patches=96,agents=24,hazards=False,predation=False,gifts=False,
                lifetime_learning=False,turn_sign=-1,turn_gain=1,record_every=ticks)
            final=result['final'];substrate=result['soil']
            rows.append(dict(seed=seed,soil_limits=enabled,
                **{k:final[k] for k in ('alive','births','meals')},**result['gardens'],
                soil=None if substrate is None else {k:substrate[k] for k in
                  ('occupied_mean','depleted_cells','occupied_cells','consumed','recovered','composted')}))
    metrics=('alive','births','meals','planted','harvests','descendant_meals','posthumous_meals')
    return dict(ablation='soil_limits',graph=str(graph),graph_sha256=hashlib.sha256(Path(graph).read_bytes()).hexdigest(),
        ticks=ticks,seeds=seeds,rules=result['rules'],decoder=dict(turn_sign=-1,turn_gain=1),
        soil_parameters={k:result['soil'][k] for k in ('size','n','recovery_per_tick','crop_cost','corpse_return')},
        rows=rows,means={name:{k:mean(row[k] for row in rows if row['soil_limits']==enabled) for k in metrics}
               for name,enabled in [('off',False),('on',True)]},
        caveat='Exploratory paired seeds; gardening stays on, only soil mode changes. This combines shared nutrient limits, '
        'recovery and replacement of compost timer boosts with nutrient returns. Initial mature food is provisioned. '
        'Recovery and initial nutrients are external inputs, not a closed nutrient cycle. Descendant/posthumous meals overlap. '
        'No migration, cooperation or biological claim; no confidence intervals. Python and browser RNGs differ.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph');parser.add_argument('--seeds',default='0,1,2,3,4')
    parser.add_argument('--ticks',type=int,default=2000);parser.add_argument('--out',default='soil-comparison.json')
    args=parser.parse_args()
    report=compare(args.graph,[int(s) for s in args.seeds.split(',')],args.ticks)
    Path(args.out).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report['means'],indent=2))
