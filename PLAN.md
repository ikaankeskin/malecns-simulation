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
- [ ] Official data acquisition and circuit selection.
- [ ] Real MaleCNS-derived circuit imported and run.

## First scientific decision

Choose an annotated visual-to-descending-neuron pathway using official MaleCNS annotations. Do not assign biological roles from arbitrary node order. Define the virtual stimulus and motor decoding explicitly, then test whether neural output responds to changes in input. Food-seeking performance is an engineered experiment, not evidence that this pathway naturally represents food or goals.
