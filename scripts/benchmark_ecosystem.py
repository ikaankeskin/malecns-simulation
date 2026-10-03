"""CPU garden scaling benchmark. Artificial ecology, not biological validation.

Run from any directory. Prints timings and full-result hashes, never bulk traces.
Use identical arguments on two revisions to compare behavior and performance.
"""
import argparse
import cProfile
import hashlib
import json
from pathlib import Path
import pstats
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ecosystem import simulate_ecosystem


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--profile', action='store_true')
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('--repeats must be positive')
    settings = dict(agents=50, max_population=50, patches=192, map_half=80,
                    gardening=True, soil_limits=True, water=True, hazards=False,
                    turn_sign=-1, turn_gain=1, record_every=6)
    circuit = ROOT / 'circuits/dng13.json'
    print(json.dumps(dict(workload='artificial garden ecology', ticks=1200, seed=4,
                         settings=settings, python=sys.version,
                         circuit_sha256=hashlib.sha256(circuit.read_bytes()).hexdigest())))
    timings, hashes = [], []
    for _ in range(args.repeats):
        start = time.perf_counter()
        result = simulate_ecosystem(circuit, 1200, 4, **settings)
        timings.append(time.perf_counter()-start)
        hashes.append(hashlib.sha256(json.dumps(result, sort_keys=True,
                      separators=(',', ':')).encode()).hexdigest())
        print(json.dumps(dict(seconds=timings[-1], result_sha256=hashes[-1])))
        del result
    print(json.dumps(dict(median_seconds=statistics.median(timings),
                         deterministic=len(set(hashes)) == 1)))
    if len(set(hashes)) != 1:
        raise SystemExit('Repeated runs produced different results')
    if args.profile:
        profiler = cProfile.Profile()
        profiler.runcall(simulate_ecosystem, circuit, 1200, 4, **settings)
        pstats.Stats(profiler).sort_stats('cumulative').print_stats(18)


if __name__ == '__main__':
    main()
