# MaleCNS Simulation

A minimal, inspectable 2D foraging loop. It takes a directed weighted neuron graph, applies bounded continuous activity updates, maps sensory inputs and motor outputs, and records every tick. **This is an exploratory controller, not a biological reconstruction.** The included `demo.json` is synthetic. **`circuits/dng13.json` contains a verified MaleCNS v1.0 subgraph: 11 neurons and 32 connections.** With the default decoder it turns away from the pellet. Reversing the turn sign is an interface choice that produces collection; it is not evidence that this pathway encodes food. See [the first experiment](docs/DNG13_EXPERIMENT.md) and [the decoder report](docs/DNG13_DECODER.md).

## Project plan

See [PLAN.md](PLAN.md) for current status and [ROADMAP.md](ROADMAP.md) for the artificial-life sequence. Each completed implementation step is committed separately. Contributor instructions are in [AGENTS.md](AGENTS.md).

## Run now (Python 3.9+, standard library)

```bash
python3 sim.py run demo.json --ticks 120 --out trace.json
```

The output records position, heading, food location, motor activity, and collection events. A fixed seed makes runs repeatable.

## Watch a 10-fly survival contest

Ten independent copies of the same circuit share a larger map and three pellets that do not respawn. Energy drains every tick; a meal can keep a fly alive to the end. Spawn pose is the only difference between flies. This is a scored toy contest, not biological competition.

```bash
python3 sim.py contest circuits/dng13.json --ticks 800 --turn-sign -1 --turn-gain 1 --out view.html --open
```

Default: 10 flies, 3 pellets, map ±20. The command prints a leaderboard and writes `view.html`. Click a fly in the sidebar to highlight its trail.

## Watch ecosystem v0.1

A persistent world: food respawns at a **new random location** after each meal, agents age, and eating extends artificial lifespan. Nearby adults reproduce; offspring inherit and mutate speed, lifespan, fertility, metabolism, and decoder gains, plus a few nearly useless quirks. MaleCNS topology stays fixed.

```bash
python3 sim.py ecosystem circuits/dng13.json --ticks 12000 --turn-sign -1 --turn-gain 1 --out view.html --open
```

Useful knobs: `--agents`, `--food-rate`, `--aging-rate`, `--repro-rate`, `--mutation-rate`, `--mutation-sigma`, `--max-population`, `--record-every`. Default runs are long enough for many generations; frames are stored every 6 ticks so the HTML stays usable. The inspector follows a living descendant when the selected agent dies. Lineage bars and contested-meal counts are on the dashboard.

## Try it in the browser

The GitHub Pages app runs the same ecosystem live. Choose a rule preset or set agent count, food spawn rate, aging rate, reproduction rate, and mutation rate, then randomize.

[Open the live ecosystem](https://ikaankeskin.github.io/malecns-simulation/)

![DNg13 ecosystem with renewable food, aging, and reproduction](docs/preview.gif)

Serve `docs/` locally if you want the same page without GitHub:

```bash
python3 -m http.server 8000 --directory docs
```

Then open http://127.0.0.1:8000/ . The published site needs GitHub Pages enabled (Actions source). The repository is private, so the public URL only works if Pages visibility allows it.

## Watch a run

The viewer is a self-contained HTML file. It replays every tick: arena, heading, food, trail, collection events, motor output, and per-neuron activity. Pause, step, reset, and a tick slider are included. The page labels the circuit as synthetic or MaleCNS-derived.

```bash
python3 sim.py view demo.json --ticks 120 --out view.html
python3 sim.py view circuits/dng13.json --ticks 500 --turn-sign -1 --turn-gain 1 --out view.html
```

Open `view.html` in a browser. Add `--open` to launch it. Generated viewers are local outputs and are not committed. Default `sim.py run` traces stay JSON.

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

Extraction tests use synthetic Arrow fixtures, test deterministic selection and retained weights, and reject missing bilateral outputs, malformed schemas, negative connections, and unverified source hashes. They require the packages in `requirements-data.txt`. Controller tests additionally check deterministic runs, stimulus responsiveness, malformed graphs, weight scaling, movement ablations, decoder validation, a synthetic decoder-sweep split, and HTML viewer playback payloads. These tests do not establish biological fidelity.

## Data attribution

MaleCNS is produced by FlyEM (HHMI Janelia), the University of Cambridge Department of Zoology, the MRC Laboratory of Molecular Biology, and Google Research. Official data is distributed under CC BY; retain the specific release license and citation with derived extracts. The derived circuit is adapted from this data: selected nodes and induced connections, plus experimental interface roles. Its original IDs and integer synapse counts are retained; the derived data remains under CC BY 4.0. Source: https://male-cns.janelia.org/download/.


### Seasonal ecology

The ecosystem now cycles through Bloom (1.65× plant lifecycle speed), Abundance (1×), Drought (0.3×), and Recovery (0.8×), each lasting 400 ticks by default. Hungry agents can sense and consume fresh corpses. Each body yields one freshness-scaled energy meal; unlike plants, it grants no lifespan bonus. Uneaten bodies decay after 180 ticks and can advance one nearby seed or growing patch by 12 timer units. These engineered rules are not claims about fly biology. The MaleCNS-derived circuit topology remains fixed.

Use `--season-length 200` to accelerate seasons, `--no-seasons` for stable growth, and `--no-scavenging` to disable corpse feeding with the `ecosystem` command. Bodies can still compost when scavenging is disabled. Maps now reflect agents at their boundaries. Python and browser runs are deterministic within each engine; their random generators differ, so equal seeds do not imply identical trajectories across engines.

The live dashboard exposes seasonal growth, corpse scavenging, and ticks per season. **Apply** restarts with the selected rules and the same seed; **Step** pauses and advances one tick. The arena tint and banner track the season, rose rings show corpse freshness, and expanding rose/green rings mark scavenging/fertilization. Select an agent to see its current target intent and dashed target line. These intent labels describe the engineered sensory target selection, not inferred cognition. Python HTML replays include season and recycling totals too.
