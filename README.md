# MaleCNS Simulation

A minimal, inspectable 2D foraging loop. It takes a directed weighted neuron graph, applies bounded continuous activity updates, maps sensory inputs and motor outputs, and records every tick. **This is an exploratory controller, not a biological reconstruction.** The included `demo.json` is synthetic. **`circuits/dng13.json` contains a verified MaleCNS v1.0 subgraph: 11 neurons and 32 connections.** With the default decoder it turns away from the pellet. Reversing the turn sign is an interface choice that produces collection; it is not evidence that this pathway encodes food. See [the first experiment](docs/DNG13_EXPERIMENT.md) and [the decoder report](docs/DNG13_DECODER.md).

## Project plan

See [PLAN.md](PLAN.md) for milestones, scientific controls, current status, and the commit workflow. Each completed implementation step is committed separately. Contributor instructions are in [AGENTS.md](AGENTS.md).

## Run now (Python 3.9+, standard library)

```bash
python3 sim.py run demo.json --ticks 120 --out trace.json
```

The output records position, heading, food location, motor activity, and collection events. A fixed seed makes runs repeatable.

## Run the real-data circuit now

No bulk download or third-party Python package is required to run the included extract:

```bash
python3 sim.py run circuits/dng13.json --ticks 500 --out trace.json
python3 sim.py run circuits/dng13.json --ticks 500 --turn-sign -1 --turn-gain 1 --out trace.json
python3 experiments.py circuits/dng13.json --out experiment.json
```

The first command uses the original avoidance decoder. The second uses the selected attraction decoder from the mapping experiment. `experiments.py` sweeps turn/sensory signs and turn gains on development seeds, then compares the selected mapping with disconnected, input-silenced, and shuffled-source controls on held-out seeds. Raw traces are local outputs. Checked-in reports: `docs/dng13-experiment.json`, `docs/dng13-decoder-experiment.json`.

## Extract a real MaleCNS circuit

The new importer streams the official Arrow connection table in batches. It selects the left/right DNg13 descending neurons and up to eight direct visual-projection inputs per output, with at least five synapses. It then retains **every** connection within the selected neurons, including weaker and recurrent connections. Neuron IDs, annotations, and raw synapse counts are preserved.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-data.txt
python3 malecns_data.py download
python3 malecns_data.py extract
python3 sim.py run circuits/dng13.json --ticks 120 --out trace.json
```

Downloads total approximately 1.07 GB. Extraction verifies pinned SHA-256 hashes before writing a real-data-labelled circuit. Existing downloads are reused; an incomplete or different release fails verification. No API token is needed. Run from the repository directory. Simulation alone requires no third-party dependencies.

[configs/dng13.json](configs/dng13.json) contains the selection rule and its scientific rationale. Provenance in each extracted graph includes source URLs, byte sizes, SHA-256 hashes, release, license, attribution, chosen inputs, and modelling assumptions. The hashes were measured from official public downloads; they are not publisher-signed checksums. Bulk data stays outside git.

DNg13 is shown in [Janelia's visual-to-movement example](https://male-cns.janelia.org/media/). This direct-input subgraph omits retinal and upstream processing. Simulator `sensory` and `motor` roles are interface assignments; the biological output class remains `descending_neuron`. Soma-side-to-world-side mapping is a hypothesis.

The current controller is a toy continuous-activity model, with no neurotransmitter signs, spikes, physiological calibration, or plasticity. Wiring plus a tuned decoder can collect synthetic food in this world; that does not establish biological food-seeking. The original CSV importer remains available for exploratory user-supplied graphs; it does not verify official provenance.

## Validation

```bash
python3 -m unittest discover -s tests -v
```

Extraction tests use synthetic Arrow fixtures, test deterministic selection and retained weights, and reject missing bilateral outputs, malformed schemas, negative connections, and unverified source hashes. They require the packages in `requirements-data.txt`. Controller tests additionally check deterministic runs, stimulus responsiveness, malformed graphs, weight scaling, movement ablations, decoder validation, and a synthetic decoder-sweep split. These tests do not establish biological fidelity.

## Data attribution

MaleCNS is produced by FlyEM (HHMI Janelia), the University of Cambridge Department of Zoology, the MRC Laboratory of Molecular Biology, and Google Research. Official data is distributed under CC BY; retain the specific release license and citation with derived extracts. The derived circuit is adapted from this data: selected nodes and induced connections, plus experimental interface roles. Its original IDs and integer synapse counts are retained; the derived data remains under CC BY 4.0. Source: https://male-cns.janelia.org/download/.
