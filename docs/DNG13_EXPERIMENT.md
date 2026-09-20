# First real MaleCNS circuit experiment

Date: 2026-09-20. Dataset: `male-cns:v1.0`.

## Result

The official-file-derived circuit is runnable and responds to directional input. It has **11 neurons, 32 directed connections, and 149 retained synapses**. It contains DNg13_L (11074), DNg13_R (512006), and nine directly connected visual-projection neurons.

The current controller **does not demonstrate effective foraging**: it collected no food over ten 500-tick intact runs. Disconnected and input-silenced controls remained stationary. A shuffled-wiring null control collected one item across ten runs, so this experiment provides no evidence that the selected biological topology improves food collection.

## Data selection and provenance

- Official downloads: https://male-cns.janelia.org/download/.
- Circuit rationale: DNg13 is featured in https://male-cns.janelia.org/media/.
- Select the two DNg13 cells annotated as `descending_neuron`, one with soma side L and one with R.
- For each output, select up to eight `visual_projection` inputs with at least five synapses. Break equal-weight ties by ascending body ID.
- Union the inputs and outputs, then retain every connection between those cells, including counts below the selection threshold and recurrent connections.
- Store IDs as strings, counts as integers, and annotations alongside the simulator roles.
- Every extraction checks project-pinned SHA-256 hashes of the complete input files. Pins were measured from HTTPS downloads of the official files, not supplied as signed checksums by Janelia.

| Input | Bytes | SHA-256 |
|---|---:|---|
| Annotations | 14,483,314 | `2177e246113e4cfbf1e7772ec37c6da1955ff22e8063d0b1f833101f99a9a3b2` |
| Connection weights | 1,051,241,946 | `e35da783d1c686b2b58b3b87cd6a403ae43bfcfba8bff28e08ef752c1a56afc1` |

Extraction streams Arrow batches rather than loading the full connection graph into Python objects. The small derived circuit is checked into `circuits/dng13.json`; bulk files are excluded from git.

## Explicit model assumptions

This is a bounded continuous-activity model. Each edge contributes its raw count divided by 100; counts are no longer clipped at 100. All edges are treated as excitatory. Neurotransmitter data has not been incorporated. Every tick is dimensionless; it is not a millisecond of biological time.

`activity_next = clip(0.75 * activity + 0.25 * (external_drive + weighted_previous_activity), 0, 1)`

Visual-projection neurons receive synthetic directional input directly. They are not retinal sensory neurons. DNg13 cells serve as the controller's output interface; they are descending neurons, not the fly's leg muscles. Soma side is used as the interface side, which is an unvalidated hypothesis about functional laterality.

The world presents a food-bearing signal to those input cells; no evidence establishes that this selected circuit naturally encodes food. The retained world mapping uses `turn = clip(0.15*(right-left), -0.3, 0.3)` and `speed = 0.13*min(1,left+right)`. An independent forward-motion bias from the synthetic starter was removed so zero motor activity means no movement.

## Static input probes

Each probe starts from zero activity, applies constant drive 0.5 to the selected input side, and runs 200 updates. Outputs are arbitrary model units. No neurons saturated in these probes.

| Input | Left DNg13 output | Right DNg13 output | Right minus left |
|---|---:|---:|---:|
| Left only | 0.188645 | 0.075445 | -0.113200 |
| Right only | 0.055270 | 0.193450 | 0.138180 |
| Both sides | 0.243914 | 0.268894 | 0.024980 |
| No input | 0 | 0 | 0 |

Directional inputs produce different neural outputs. With the existing world turn rule, a left-sided signal tends to produce a negative turn, suggesting that the current decoder's sign may be inappropriate for an attraction task. That is a hypothesis for the next experiment, not evidence about DNg13's natural function. Do not tune a decoder and then claim that food seeking emerged from anatomy alone.

## World controls

Ten seeds (0–9), 500 ticks each. Agents start at the origin facing +x. Initial food lies at radius 6 with a seeded random angle. Seeds also determine later food placement. The shuffled control independently shuffles presynaptic IDs across the existing weighted edges; it preserves target weight totals and the multiset of presynaptic IDs, but may create self/parallel connections. It is only one null-model family.

| Condition | Mean food collected per run | Mean distance travelled |
|---|---:|---:|
| Intact | 0.0 | 7.279841 |
| Disconnected | 0.0 | 0.0 |
| No sensory input | 0.0 | 0.0 |
| Shuffled sources | 0.1 | 12.408987 |

These ten exploratory seeds are not a statistical performance study. There is no training, plasticity, full-CNS reconstruction, or biological behavioural validation. Detailed values, controller parameters, seeds, and circuit checksum are in `docs/dng13-experiment.json`.

## Reproduce

Run from the repository root. The checked-in circuit runs without downloading the full dataset:

```bash
python3 sim.py run circuits/dng13.json --ticks 500 --out trace.json
python3 experiments.py circuits/dng13.json --ticks 500 --seeds 10 --out experiment.json
```

To reproduce the circuit from the official files:

```bash
python3 -m pip install -r requirements-data.txt
python3 malecns_data.py download
python3 malecns_data.py extract --out /tmp/dng13-reproduced.json
```

Compare the output with `circuits/dng13.json`. The JSON is deterministic for the pinned release and config. Test fixtures are synthetic and cannot pass official-release checksum verification.

## Decoder follow-up

Completed. Turn/sensory signs and turn gain were compared on seeds 0–9, then the selected mapping was tested on seeds 10–19 against shuffled, disconnected, and no-input controls. The default decoder still collects nothing. `turn_sign=-1`, `turn_gain=1.0` collected a mean of 4.0 items on held-out seeds versus 0.5 for shuffled wiring. Report: [DNG13_DECODER.md](DNG13_DECODER.md).

## Viewer

Completed. `python3 sim.py view` writes a self-contained HTML replay with pause, step, reset, a tick slider, motor traces, and per-neuron activity. The page labels synthetic vs MaleCNS-derived circuits. Generated HTML is a local output.

## Next experiment

Neurotransmitter-aware dynamics and learning remain separate later milestones.

## Attribution and license

The derived data is adapted from MaleCNS v1.0 by FlyEM (HHMI Janelia), the University of Cambridge Department of Zoology, MRC Laboratory of Molecular Biology, and Google Research, under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Changes: node subset, connection subset, summed duplicate pairs, and added experimental simulator roles. These authors do not endorse the simulator or its assumptions. Source links and release are retained in the graph.
