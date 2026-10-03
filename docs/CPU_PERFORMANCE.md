# CPU garden scaling measurement — 2026-10-03

This is a software performance measurement of artificial ecology, not biological validation. The bundled `circuits/dng13.json` supplies the MaleCNS v1.0-derived 11-node/32-edge controller with its existing provenance; movement decoding, seed dispersal, soil and water remain engineered assumptions. No biological dataset was downloaded or modified.

## Reproduce

```sh
python scripts/benchmark_ecosystem.py --repeats 3 --profile
```

Standard-library Python suffices. The runner resolves the bundled circuit relative to the repository, prints settings, circuit checksum, wall times and SHA-256 of the complete sorted compact JSON result, and checks repeatability. Hashing is outside the timed simulation. It retains no generated traces. Compare the same runner/settings on the baseline revision `7dc3fca` and the current revision; profiling has overhead and must not be compared directly with unprofiled wall time.

Workload: seed 4, 1,200 ticks, 50 initial agents (the CPU input limit), population cap 50, 192 initial patches, map half-width 80, gardening/soil/water enabled, hazards disabled, decoder turn sign −1 and gain 1, recording every 6 ticks. Other settings retain engine defaults, including reproduction and communication. This scales the prior 24-agent/96-patch garden workload without relaxing safeguards.

## Bottleneck and change

Baseline cProfile: 9.918 seconds cumulative simulation; motors 3.336 seconds, patch snapshots 2.066, gardening placement 1.092, neural steps 0.718, soil growth 0.534. Copying and spatial scans merit CPU work before a neural accelerator. Snapshot-copy experiments did not show a reliable wall-time gain and were reverted.

The retained change counts planted gardens once per placement phase and increments that count after each successful planting. After the 64-garden limit is reached, carriers skip distance/spacing scans. Dead and expired seeds still clear first. Sorted agent order, spacing, energy, events and RNG behavior are preserved. The browser engine is unchanged and uses the same existing cap rules.

## Behavior and timings

Python 3.12.14, macOS 26.6 arm64. Three alternating before/after pairs in one process used the baseline placement function and the optimized function with otherwise identical code:

| Pair | Before seconds | After seconds |
| --- | ---: | ---: |
| 1 (before first) | 12.562 | 10.468 |
| 2 (after first) | 9.680 | 7.632 |
| 3 (before first) | 9.334 | 3.683 |

All six complete outputs had SHA-256 `44d3c72f01c6c258b167cfe79fc47159ba1e7aa1377c2f0e305482bba00b4049`, including every recorded frame, event, final metric and roster. Final population was 50 with 326 meals. Initial baseline-only runs were 3.450/3.587/3.580 seconds. Host timing varied substantially during this session: the paired results favor the change but do not establish a stable speedup percentage. Repeat under controlled load before making a throughput promise or choosing acceleration.

Validation: all 114 software tests passed, including synthetic last-slot priority, same-tick capacity enforcement, expired/dead-seed cleanup without spacing scans, deterministic replay and recording-cadence invariance. Existing Python/JavaScript garden and water checks remain in the suite. These checks do not validate real MaleCNS biological behavior.
