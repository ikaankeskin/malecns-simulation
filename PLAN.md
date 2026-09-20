# Implementation plan

## Goal
Build an inspectable artificial-life simulation whose agents are controlled by circuits derived from the MaleCNS connectome. Start on CPU with a small, reproducible circuit; measure before moving to GPU or multiple agents.

## Milestones and completion criteria

1. **Repository foundation** — private GitHub repository; README, roadmap, contributor instructions; preserve the runnable synthetic baseline. Commit: `chore: establish simulation baseline and project roadmap`.
2. **Real-data pipeline** — obtain official MaleCNS v1.0 annotations and connectivity, select a documented sensory-to-descending-neuron circuit, retain actual neuron IDs and synapse counts, and record source URLs, hashes, extraction choices, and attribution. Support offline inputs and fail clearly when authentication or data is missing. Commit code separately from any verified data extract.
3. **Validated circuit controller** — distinguish measured topology from assumed dynamics and sensory/motor mapping; add explicit neurotransmitter policy, input scaling, activity diagnostics, and meaningful malformed-data tests. Verify responsiveness against disconnected and shuffled-graph controls. A successful run does not by itself validate biological fidelity.
4. **Visible simulation** — render the world and neural activity with pause, step, reset, deterministic seeds, and exportable traces. Display the loaded circuit's provenance and whether it is synthetic or MaleCNS-derived.
5. **Learning experiment** — introduce a documented plasticity rule only after fixed-circuit controls work. Compare learning enabled/disabled over held-out seeds; track reward, saturation, and stability.
6. **Multiple agents and acceleration** — give each agent independent state, profile CPU cost and memory, then implement a batched GPU backend if measurements justify it. Keep a CPU path for local Mac development.

## Working agreement

- Commit every completed, validated step with a descriptive message; push to the private repository when accessible.
- Never silently substitute synthetic data for unavailable MaleCNS data.
- Keep credentials, raw bulk data, environments, and generated run output out of git.
- Preserve source attribution and provenance of derived datasets.
- Record completed work and remaining blockers in this file.
- Do not claim biological intelligence, whole-CNS simulation, or learning without evidence.

## Status

- [x] Synthetic baseline: 6 nodes, 4 edges, deterministic foraging loop and JSON traces.
- [x] Initial smoke run: 120 ticks, one food collection (demonstration only).
- [x] Repository documentation and step-by-step commit policy prepared.
- [x] Private repository created: `ikaankeskin/malecns-simulation`.
- [x] README, implementation plan, contributor instructions, and synthetic starter committed to `main`.
- [x] Official data acquisition and circuit selection: bilateral DNg13 plus direct visual-projection inputs.
- [x] Streaming Arrow importer, SHA-256 release verification, documented assumptions, and six focused extraction tests.
- [x] Checked-in real-data extract and controller experiment report: 11 neurons, 32 connections, 149 synapses.
- [x] Real MaleCNS-derived circuit imported and run; directional response confirmed.
- [x] Eleven focused tests pass; disconnected and no-input controls stay stationary.
- [x] Decoder mapping experiment: 12 sign/gain candidates on seeds 0–9; held-out seeds 10–19. Selected `turn_sign=-1`, `turn_gain=1.0` collected mean 4.0 food versus 0 baseline and 0.5 shuffled. Interface result, not biological foraging.
- [x] Visible simulation: self-contained HTML playback with pause, step, reset, per-neuron activity, and synthetic vs MaleCNS-derived labels.
- [x] Multi-agent CPU contest: 10 independent flies, scarce shared food, larger map, energy/survival ranking. Same circuit and decoder; spawn pose differs. See `python3 sim.py contest`.
- [x] Ecosystem v0.1: renewable patches, age, starvation/old-age death, decaying corpses, event timeline, inspector. See `ROADMAP.md` and `python3 sim.py ecosystem`.
- [x] Reproduction: proximity + energy cost, parent IDs, generation, population cap. Topology stays fixed.
- [x] GitHub Pages live ecosystem with agent/food/aging/reproduction controls and randomize.
- [ ] Genetics, combat, social, and LLM layers (not started).
- [ ] Neurotransmitter-aware dynamics and later learning experiments.

## First scientific decision

Choose an annotated visual-to-descending-neuron pathway using official MaleCNS annotations. Do not assign biological roles from arbitrary node order. Define the virtual stimulus and motor decoding explicitly, then test whether neural output responds to changes in input. Food-seeking performance is an engineered experiment, not evidence that this pathway naturally represents food or goals.

## Development record

- `348ee16`: streaming data importer, official-release checksums, selection config, and six extraction tests.
- Follow-up experiment: include the real subgraph, circuit validation and ablations, remove independent locomotion, preserve unclipped synapse-count ratios, and report the negative foraging result. See `docs/DNG13_EXPERIMENT.md`.
- Decoder experiment: parameterize turn/sensory signs and turn gain; select on development seeds; evaluate intact vs shuffled/disconnected/no-input on held-out seeds. See `docs/DNG13_DECODER.md`.
- Viewer: `python3 sim.py view` writes a self-contained HTML replay of world state and neural activity. Generated `view.html` stays local.
- Multi-agent contest: independent circuit copies, three non-respawning pellets, energy drain, deterministic leaderboard. Engineered scoring, not fly physiology.
- Ecosystem v0.1: persistent patches with a growth lifecycle, age, labelled deaths, decaying corpses, charts, and timeline.
- Reproduction: two nearby adults that meet age and energy thresholds produce an offspring with a new circuit copy. No mutation. Population is capped.
- GitHub Pages: `docs/index.html` runs the ecosystem in the browser; sliders and Randomize retune the world.
