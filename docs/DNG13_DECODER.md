# DNg13 decoder mapping experiment

Date: 2026-09-21. Dataset: `male-cns:v1.0`. Circuit: `circuits/dng13.json` (same extract as the first experiment; SHA-256 `1697c9b68d30cd23b2f05e78dfaa8b3ac228e2b8addfd0a5ee3ef69ed283b772`).

## Result

The default world mapping still collects no food. Reversing the turn decoder, with sensory laterality unchanged, produces collection. On ten previously unused seeds the selected mapping collected a mean of **4.0** items; the baseline mapping collected **0**; a shuffled-wiring control with the same decoder collected **0.5**. Disconnected and input-silenced controls remained stationary.

This is an engineered interface result. It does **not** show that DNg13 encodes food, goals, or foraging. The circuit, stimulus, and motor rule are the same toy model as before. Only the sign and gain of the decoder were varied.

## Question and protocol

The first experiment found ipsilateral visual-projection → DNg13 weights and a `turn = clip(0.15*(R-L))` rule that turns away from the pellet. This follow-up treats sensory laterality and motor decoding as experimental parameters.

- Development seeds: 0–9, the same ten used in the first report.
- Held-out seeds: 10–19, not used for selection.
- 500 ticks per run. Food starts at radius 6 with a seeded angle. Agent starts at the origin facing +x.
- Candidate grid: `sensory_sign ∈ {+1, −1}`, `turn_sign ∈ {+1, −1}`, `turn_gain ∈ {0.15, 0.50, 1.00}` (12 mappings). Speed gain and turn clip stay at 0.13 and 0.3.
- Selection rule, fixed before looking at held-out data: keep candidates whose mean saturated fraction is ≤ 0.25; maximize mean food collected, then minimize mean closest approach to the first pellet; decoder name is the deterministic tie-break.

`turn_sign = -1` replaces `(R-L)` with `(L-R)`. `sensory_sign = -1` swaps the left/right stimulus assignment. Flipping both is a double negative and should remain an avoidance mapping.

## Development sweep

| Decoder | Mean food | Mean closest approach | Mean distance | Mean saturation |
|---|---:|---:|---:|---:|
| sensory+1 turn+1 gain 0.15 (baseline) | 0.0 | 5.743 | 7.280 | 0.006 |
| sensory+1 turn+1 gain 0.50 | 0.0 | 5.899 | 6.508 | 0.001 |
| sensory+1 turn+1 gain 1.00 | 0.0 | 5.946 | 6.401 | 0.000 |
| sensory+1 turn−1 gain 0.15 | 1.7 | 0.601 | 30.046 | 0.150 |
| sensory+1 turn−1 gain 0.50 | 3.8 | 0.344 | 28.602 | 0.069 |
| **sensory+1 turn−1 gain 1.00 (selected)** | **3.9** | **0.362** | **28.722** | **0.078** |
| sensory−1 turn+1 gain 0.15 | 1.5 | 0.373 | 27.226 | 0.106 |
| sensory−1 turn+1 gain 0.50 | 3.7 | 0.342 | 28.435 | 0.067 |
| sensory−1 turn+1 gain 1.00 | 3.8 | 0.360 | 27.884 | 0.080 |
| sensory−1 turn−1 gain 0.15 | 0.0 | 5.675 | 7.478 | 0.006 |
| sensory−1 turn−1 gain 0.50 | 0.0 | 5.856 | 6.610 | 0.001 |
| sensory−1 turn−1 gain 1.00 | 0.0 | 5.918 | 6.444 | 0.001 |

Avoidance mappings (same sign on sensory and turn, including baseline) never collected food. Attraction mappings (exactly one sign flipped) did. Higher turn gain improved collection without crossing the saturation limit. Selected mapping: `turn_sign=-1`, `turn_gain=1.0`, `sensory_sign=+1`.

## Held-out controls

Ten seeds (10–19), selected decoder unless noted. Per-seed collection for intact+selected was `[4, 5, 4, 3, 3, 1, 6, 4, 6, 4]`. Shuffled+selected was `[0, 0, 0, 3, 0, 1, 0, 0, 1, 0]`.

| Condition | Mean food collected | Mean closest approach | Mean distance travelled |
|---|---:|---:|---:|
| Intact, baseline decoder | 0.0 | 5.045 | 9.011 |
| Intact, selected decoder | 4.0 | 0.349 | 32.625 |
| Shuffled sources, selected decoder | 0.5 | 3.692 | 19.498 |
| Disconnected, selected decoder | 0.0 | 6.000 | 0.000 |
| No sensory input, selected decoder | 0.0 | 6.000 | 0.000 |

Given this decoder, the intact wiring collected more food than shuffled sources. That is evidence that topology is not irrelevant once the interface attracts rather than avoids. It is not evidence of a biological feeding programme. The shuffled control is one null-model family; it can create self-connections and parallel edges.

## Model assumptions (unchanged)

Bounded all-excitatory rate model; synapse counts divided by 100; no neurotransmitter signs, spikes, or physiological time. Visual-projection neurons are driven as if they were sensors. DNg13 cells are used as a left/right motor interface; they are descending neurons, not muscles. Soma side is an unvalidated laterality hypothesis. The world “food” signal is a synthetic directional cue.

## Reproduce

```bash
python3 experiments.py circuits/dng13.json --ticks 500 --development-seeds 10 --held-out-seeds 10 --out docs/dng13-decoder-experiment.json
python3 sim.py run circuits/dng13.json --ticks 500 --turn-sign -1 --turn-gain 1 --out trace.json
python3 sim.py view circuits/dng13.json --ticks 500 --turn-sign -1 --turn-gain 1 --out view.html
```

Default `sim.py` flags keep the original avoidance decoder. Controller tests cover decoder validation and sign reversal on the synthetic `demo.json` graph; those tests are not MaleCNS validation. Detailed values are in `docs/dng13-decoder-experiment.json`.

## Attribution and license

The derived circuit is adapted from MaleCNS v1.0 by FlyEM (HHMI Janelia), the University of Cambridge Department of Zoology, MRC Laboratory of Molecular Biology, and Google Research, under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). These authors do not endorse the simulator or the selected decoder.
