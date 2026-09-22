# Implementation plan

## First drought mission — engine
- Fixed seed 4, 24 founders, 96 patches, map half 80, no reproduction, hazards or predation. Seasons last 400 ticks; finish at tick 1200 before returning rain is applied. Win requires 8 living agents and 3 distinct garden soil cells at least 20% moist. Extinction ends early.
- Completed missions freeze simulation and watering. Mission action records persist separately from the rolling event timeline; retries recreate the same world and reserve.
- Tuning observation: seed 4 without intervention finishes with 8 survivors and no moist garden cells. Three distinct cells watered immediately before the final tick meet the introductory goal. This intentionally teaches reserve timing; it is not evidence that watering increases survival or meals. Harvest-based goals need further balancing.
- Validation: deterministic no-action loss, watered success, unique-cell accounting, reserve debit, terminal freeze, fresh retry and early extinction covered by `node tests/mission.cjs` (synthetic game checks).

## Rivers and water — resource model completed
- Seeded river geometry, seasonal rain, evaporation, bank moisture and conservative diffusion now feed shared crop budgets in Python and JavaScript. Water enables soil limits; disabled mode preserves the baseline.
- Added `--water`, independent trace snapshots and a finite irrigation reserve for the upcoming player controls.
- Validation: eight focused synthetic soil/water tests pass, including conservation, bounds, drought starvation, reserve exhaustion and cross-engine parity; live-page wiring smoke test passes. These are software checks, not biological validation.

## Riverkeeper player prototype
- Added visible rivers, fertility/moisture overlay selection, weather countdown, patch moisture, finite watering reserve, event logging and slow/normal/fast playback. Garden-world preset enables water and seasons. Reset restores the reserve.
- Player watering affects a shared soil cell rather than granting an immediate meal. Wild patches cannot be watered through the player control. Replay shows the recorded river and water state without editable actions.
- Validation: 107 synthetic software tests pass, including player-button reserve debit, event logging, slow playback and reset. Browser layout verification is tracked separately.
- Live verification caught a malformed moisture option and an old cached engine loaded with new controls. Corrected the option markup and versioned the script URLs together for this release.
- Next: tune and implement a first-drought mission with an explicit result and retry, before channels, cisterns or floods. See ROADMAP.md for gameplay priorities and README.md for controls and limitations.

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

- [x] Live soil verification (2026-09-22): garden shortcut enabled soil; disabling it and applying showed unrestricted growth. At tick 1935, 31/87 occupied cells were below 20% fertility. P96's six samples showed recovery from 0% at tick 1356 to 38% at tick 1856, with 45% current fertility. Overlay and patch history verified visually; no app-origin browser error observed. Changed the nutrient dashboard label to “compost events” because soil mode replenishes cells rather than directly fertilizing one plant.

- [x] Soil observatory and paired comparison: live/replay fertility overlay, mode toggle, occupied-cell fertility/depletion metrics, nutrient accounting and bounded garden soil history. Garden-world shortcut now enables soil mode. Five seeds at 2,000 ticks: soil off/on alive 45.6/10.2, births 83.8/40.4, garden harvests 439.6/59; planting stays on and both modes reach the garden cap. No migration claim. Full suite: 104 passing tests; CLI soil replay generated and scripts/payload parsed.

- [x] Shared-soil engine: optional grid of cells up to 10 units wide, capacity 1, recovery 0.0008/tick, growing-stage cost 0.6 per crop, proportional same-cell allocation. Uneaten corpses return up to 0.3 to their cell, replacing the timer shortcut in this mode. Six fertility samples per patch; aggregate nutrient accounting and immutable replay snapshots. Disabled mode retains the prior ecosystem. Synthetic budget, fairness, recovery, compost, growth-completion and Python/JavaScript parity tests added.

- [x] Live garden verification (2026-09-22): deployed large-world button, 2× follow camera and patch selection worked. P96 showed F9 planting at tick 56 from wild P70 and remained at (-46.6, 50.9). At tick 171 the live world had 19 gardens and visible carried seeds. Garden list height is bounded so history remains accessible as it fills. Replay script/payload parsing passed. A separate browser-engine run reached 2,000 ticks with 230 descendant meals and 180 posthumous meals (seed 4; not a cross-engine trajectory match).

- [x] Large-world garden observatory: 40/80/160-unit square worlds; starting food scales by area up to 192; one-click 24-agent garden setup; 2×/4× follow camera; carried-seed marks, persistent garden outlines, clickable patch history and replay garden inspector. Five seeds at 2,000 ticks: planting off/on alive 13.4/45.6, births 45.4/83.8, meals 241.2/618.2. On runs all reached the 64-garden cap; mean descendant/posthumous meals 244.4/195.2 (overlapping counters). Validation: 99 tests, CLI playback generation, paired-run repeatability, and a 2,000-tick browser-engine smoke run. Soil depletion and resource-limited garden growth remain future work.

- [x] Persistent garden engine: one carried seed from a plant meal, 600-tick expiry, minimum 20-tick carry and 3-unit displacement, 2-unit patch spacing, 0.08 planting cost with 0.8 energy eligibility. At most 64 added gardens. Gardens retain their coordinates and ancestry through regrowth and planter death; bounded recent eaters plus descendant/posthumous meal counters. Python and browser implementations preserve the disabled baseline. Soil depletion remains a later phase.

- [x] Live helper verification (2026-09-22): Pages deployment succeeded for `de8ab36`; both toggles applied, gifts transferred energy, and F1 displayed F2 as a past helper (0.088 remembered energy at tick 255 from a tick-183 gift). Preview captured. Software suite: 94 passing tests.

- [x] Helper observatory and ablation: optional live control, animated transfer trails, per-agent helper evidence in live and replay inspectors, and five paired seeds with gifts held on. Preference off/on: births 7/7, meals 27.6/27.6, alive 0/0, gifts to remembered donors 5.4/6.0. No survival benefit in this sample. Validation: 94 tests pass, including cross-engine helper fixtures and executable page controls.

- [x] Helper memory engine: received energy per giver, eight records, 400-tick half-life and 1,200-tick expiry. Optional reciprocity biases recipient distance; gifts and reciprocity remain off by default. Same-tick gifts do not count as prior help. Python/JavaScript synthetic parity and energy-loss checks included. This extends the existing gifts and generosity without changing circuit topology or the default trajectories.

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
- [x] Evolution of simulation parameters: offspring blend parent genomes and mutate turn/sensory/metabolism/speed/lifespan/fertility, plus weak quirks. Connectome topology remains fixed.
- [x] Random food respawn, meal-extended lifespan, inspector follow-on, competition metrics, and a lineage dashboard.
- [x] Local food signals, bounded location memory, inherited signalling/response tendencies.
- [x] Ecology comparison: seasons × scavenging, five seeds, living-founder counts. See `docs/ecology-comparison.json`.
- [x] Family trees: depth-capped ancestors and descendants for the selected agent, including cause of death.
- [x] Map hazards: three seeded discs, escape cue, and death causes in the order predation, hazard, starvation, old age.
- [x] Costly energy gifts: the recipient keeps less than the donor pays, default off.
- [x] Optional predation: a costly attack that can kill, default off, corpse scavenged under the existing rules.
- [x] Inherited caution, generosity, and aggression. Neutral scale is 1. One gene varies at a time.
- [x] Lifetime gift and attack scores. Individual, decaying, and not inherited. Synapses stay fixed.
- [x] DNg13 neurotransmitter signs from the aggregate table. Glutamate edges dropped; no GABA in this extract. The live controller stays all-positive.

## First scientific decision

Choose an annotated visual-to-descending-neuron pathway using official MaleCNS annotations. Do not assign biological roles from arbitrary node order. Define the virtual stimulus and motor decoding explicitly, then test whether neural output responds to changes in input. Food-seeking performance is an engineered experiment, not evidence that this pathway naturally represents food or goals.

## Development record

- `348ee16`: streaming data importer, official-release checksums, selection config, and six extraction tests.
- Follow-up experiment: include the real subgraph, circuit validation and ablations, remove independent locomotion, preserve unclipped synapse-count ratios, and report the negative foraging result. See `docs/DNG13_EXPERIMENT.md`.
- Decoder experiment: parameterize turn/sensory signs and turn gain; select on development seeds; evaluate intact vs shuffled/disconnected/no-input on held-out seeds. See `docs/DNG13_DECODER.md`.
- Viewer: `python3 sim.py view` writes a self-contained HTML replay of world state and neural activity. Generated `view.html` stays local.
- Multi-agent contest: independent circuit copies, three non-respawning pellets, energy drain, deterministic leaderboard. Engineered scoring, not fly physiology.
- Ecosystem v0.1: persistent patches with a growth lifecycle, age, labelled deaths, decaying corpses, charts, and timeline.
- Reproduction: two nearby adults that meet age and energy thresholds produce an offspring with a new circuit copy. Population is capped.
- Parameter evolution: genomes include speed, lifespan, fertility, metabolism, decoder gains, and nearly-neutral quirks. Mutation does not edit MaleCNS connectivity.
- Random food: a patch relocates when it leaves cooldown. Meals extend artificial lifespan.
- Dashboard: living descendants per founder, generation histogram, contested meals.
- GitHub Pages: `docs/index.html` runs the ecosystem in the browser; sliders and Randomize retune the world.


- Browser-engine repair: remove a duplicated closing block that prevented JavaScript parsing; add a Node execution smoke test to the Python test suite.

### Seasonal ecology and nutrient recycling
- Added deterministic Bloom → Abundance → Drought → Recovery cycles; seasonal multipliers scale plant lifecycle timers.
- Hungry agents sense fresh corpses through the existing controller. Scavenging consumes one corpse, restores freshness-scaled energy, and does not extend lifespan.
- Unconsumed corpses can accelerate the nearest immature plant within five map units when they decay. Consumed bodies cannot compost.
- Enforced reflecting finite map boundaries in both engines. Added CLI season/scavenging switches and playback rule forwarding.
- Validation: 44 tests pass, including synthetic cross-engine ecology fixtures, meal eligibility, deterministic replay, and map bounds. These are software checks, not biological validation.
- Next step: expose environment, nutrient events, and target intent in live and replay views.

### Ecology dashboard and replay controls
- Added seasonal growth and scavenging toggles, season duration, season banner, tinted arena, freshness rings, nutrient-event highlights, and aggregate recycling counts.
- Inspector shows current target intent and scavenging count, with a dashed target line. Corrected displayed lifespan to respect the meal bonus cap.
- Added a paused single-step control and kept plant-maturation chatter out of the live timeline. Python replay shows season and recycling totals.
- Validation: 45 tests pass, including executable synthetic DOM/canvas wiring checks for pause, step, restart, toggles and season transitions; CLI playback generation also passes. Local browser preview was blocked by the browser network boundary; DOM harness is not a layout test.

### Deployment verification (2026-09-21)
- UI commit `d2c1bbb` is pushed; Pages run `35546419914` failed at `actions/configure-pages@v5`, before upload/deploy. Browser confirmed the Pages URL returns 404. No live visual verification is claimed.
- Repository Pages configuration needs investigation before release. The current GitHub connector has no Pages administration capability. No repository visibility or permissions were changed.

### Food signals and bounded memory
- Added local FOOD reports with range, cost, cooldown and expiry. Receivers may remember four locations and six recent outcomes; hidden patch movement never updates a remembered location.
- Added inherited signalling/responsiveness tendencies and a deterministic decision stream separate from world RNG. Memory supplies a virtual sensory target; the independent MaleCNS-derived circuit still controls locomotion. No cooperation reward or LLM.
- Tracks sent/received reports, followed memories, meals, empty arrivals and expired trips. Signal-associated meals are observations, not proof that a signal caused a meal.
- Python and JavaScript synthetic fixtures agree; 51 tests pass. A browser-engine smoke run with DNg13, seed 4, 2,000 ticks produced 99 reports, 121 followed memories, 13 associated meals and 47 empty arrivals; population extinct by the end. This is a smoke run, not evidence of improved survival.
- User reports Pages deployment now works. Next: dashboard visibility and a repeatable on/off comparison.

### Social observatory
- Added communication on/off and sensory-range controls, violet broadcast rings, remembered-goal lines, per-agent memories and factual recent outcomes.
- Live and replay views show report and arrival metrics; inherited signalling/response tendencies are visible in the live inspector.
- Synthetic page wiring tests cover disabling/re-enabling communication alongside pause, step and restart. These checks do not establish browser layout or biological fidelity.

### Communication ablation and release verification
- Added `social_experiment.py` and a synthetic repeatability test; full suite: 52 passing tests.
- Five seeds, 2,000 ticks, sensory range 12: communication off/on mean final alive 0/0.6, births 9.4/9.6, plant meals 39.6/33.8. Mixed exploratory results; no general benefit or causal attribution claim.
- Browser verified the deployed social dashboard, advancing counters, memory/outcome readouts, communication toggle and step/restart controls. Captured visible violet food reports; no app-origin console error observed.
- Next: bounded per-sender reliability learning, with explicit controls for messaging cost, memory and sensory-target policy before any LLM layer.

### Per-sender reliability engine
- Each agent learns perceived report usefulness from actual arrivals: meals add positive evidence, empty locations add negative evidence. Expired trips provide no feedback; an empty arrival is not evidence of deception.
- Neutral score 0.5; evidence decays with a 400-tick half-life, is capped at 16, and is retained for at most eight senders (oldest outcome first, source ID breaks ties).
- Twice the score scales the inherited response tendency for new reports; existing goals, locomotion, circuit topology and genomes are unchanged. Learned records are individual state, not inherited traits.
- `--no-social-learning` keeps the previous fixed-response communication baseline. Python snapshots expose read-only decayed records. Matching JavaScript implementation included.
- Validation: 59 tests pass, including neutral prior, feedback direction, decay, capacity/eviction, disabled mode, agent independence, response effects and Python/JavaScript parity.

### Reliability observatory and controlled comparison
- Added a learning toggle, per-sender scores/decayed evidence/effective acceptance chances, and score feedback on recent arrival outcomes. Playback displays sender scores.
- Added `social_experiment.py --learning` to hold communication on while toggling only learning. The original communication ablation now explicitly keeps learning off for reproducibility.
- Five seeds, 2,000 ticks, range 12: learning off/on final alive 0.6/1.0, births 9.6/10.2, meals 33.8/31.4. Results remain mixed and exploratory; full aggregate report checked in.
- Full test suite: 60 tests pass, including the live control wiring and repeatable paired-learning comparison.
- Live browser verified the learning toggle, fixed-response disabled mode, and a populated record (F5 rated F6 65/100 after a meal, with evidence decay visible). No application-origin browser errors observed.
- Corrected report circuit checksums to match the canonical GitHub blob: the local materialized copy had an extra trailing newline. JSON/circuit semantics and measured results were unchanged. Added a regression check; 61 tests now pass.

### Next-phase plan
- Wrote [docs/NEXT_PHASES.md](docs/NEXT_PHASES.md) for the eight remaining items, in dependency order, each with a source project, an implementable slice, and a claim limit.
- Locked the open choices: cooperation is a directed energy gift, predation can kill, and neurotransmitter signs use acetylcholine and GABA only. Glutamate and monoamines are not applied.

### Ecology comparison
- Added `ecology_experiment.py`, a 2×2 of seasons and scavenging with composting left on. Five seeds, 2,000 ticks, range 12.
- Means, seasons/scavenging: on/on alive 1.0, births 10.2, meals 31.4, scavenged 12.4, living founders 0.2; on/off 0 / 8.2 / 32.2 / 0 / 0; off/on 0.6 / 10.8 / 31.2 / 13.8 / 0.4; off/off 0 / 8.2 / 28.8 / 0 / 0. Exploratory only. The both-on cell matches the earlier learning-on social run.
- Validation: ecology runner repeatability plus the canonical circuit checksum. No new world rule.

### Family trees
- Added a depth-capped pedigree of the selected agent. Nodes show generation, alive or cause of death, and both parents. Relatives past four generations are counted as omitted. Siblings are not treated as descendants.
- Playback carries a roster so decayed agents stay on the tree. The live inspector uses the same rule.
- Validation: synthetic depth, death-tick, and unborn checks, plus a reproduction run whose child lists both parents. The live page showed a selected descendant with named ancestors and offspring. Node could not execute here because its ICU library is missing; the page's own JavaScript matched the Python fixture for the depth-1 case.

### Map hazards
- Added three seeded discs that drain 0.02 energy per tick while an agent stands inside. Placement does not use the food random stream. Within sensory range, a disc competes with food: the agent steers away when the edge is closer than the meal. The circuit still only receives a direction.
- Death labels, first match: predation (reserved), hazard, starvation, old age. `--no-hazards` and the live checkbox turn the discs off.
- Five seeds, 2,000 ticks, range 12: hazards off/on alive 1.0/0, births 10.2/3.2, plant meals 31.4/17.4. Hazard-labelled deaths were 0/0. The off cell matches the earlier both-on ecology means. Exploratory; avoidance changed foraging, and this sample did not die inside a disc.
- Validation: placement stability, food positions unchanged, escape priority, death order, and a forced disc kill. The live page drew the discs and removed them after Apply with the checkbox off. Browser placement for seed 4 matched Python.

### Energy gifts
- Added an optional directed gift. The donor pays 0.15 and the neighbour within 4 units keeps 0.10, on an 80-tick cooldown, with a fixed attempt chance until a generosity gene exists. A later count records whether the recipient is alive after 100 ticks. That count is not evidence the gift saved them.
- Default off. The comparison holds hazards off so the gift is the only change against the social baseline.
- Five seeds, 2,000 ticks, range 12: gifts off/on alive 1.0/0.8, births 10.2/11.6, plant meals 31.4/38.2, gifts sent 0/30.2, energy paid 0/4.53, energy kept 0/3.02. Exploratory. The off cell matches the earlier ecology both-on means.
- Validation: transfer loss, cooldown, disabled mode, and repeatable paired runs. The live checkbox is off by default. The browser transfer matched the Python energies.

### Optional predation
- Added a default-off attack. Range 2, shorter than sensory range. Cost 0.08, damage 0.45, cooldown 40, and a fixed attempt chance when a neighbour is closer than the nearest mature plant and energy is above 0.5. A killing blow is labelled predation. The attacker gains no meal; the corpse uses the existing scavenging rule, which does not allow a meal on the tick of death.
- Comparison holds hazards, seasons, scavenging, gifts, and sender learning fixed. Five seeds, 2,000 ticks, range 12: predation off/on alive 0/0, births 3.2/1.8, scavenged 4.4/3.2, predation deaths 0/1.4, starvation 0.8/2.2, old age 10.4/6.2. The off cell matches the earlier hazards-on run. Exploratory.
- Validation: kill without a meal, food-closer block, range block, disabled mode, and repeatable paired runs. The live checkbox is off. The browser attack matched the Python kill.

### Personality
- Added three inherited scales, each neutral at 1 and clamped from 0 to 2. Caution multiplies how far a hazard can be and still beat food. Generosity multiplies the gift attempt chance. Aggression multiplies the attack attempt chance. Standing inside a disc still repels. Offspring blend the genes and mutate them with additive noise, like signalling. A frozen gene stays at 1 and does not draw a mutation.
- Comparison leaves hazards, seasons, scavenging, gifts, predation, and sender learning on. One gene mutates; the other two stay at 1. The all-frozen world is shared. Five seeds, 2,000 ticks, range 12. Frozen means: alive 0, births 1.4, gifts 4.2, attacks 5.2, hazard entries 1, gene mean 1. Varying caution: births 1.8, gifts 5.6, attacks 5.6, entries 1.4, gene mean 0.9972. Varying generosity: births 2.8, gifts 6.8, attacks 6.8, entries 1.6, gene mean 0.9992. Varying aggression: births 2.6, gifts 6.4, attacks 6.8, entries 1.6, gene mean 0.9998. Population means stayed near 1 because few offspring were born. Exploratory. These are tendencies, not character traits.
- Validation: caution changes the food-versus-hazard choice, zero generosity blocks a certain gift, aggression scales a failed roll into an attack, a frozen gene stays at 1, and a stay inside a disc counts as one entry. The inspector shows 1.00 / 1.00 / 1.00 on a founder. The browser hazard choice and blocked gift matched Python.

### Lifetime action scores
- Added one decaying score for gifts and one for attacks. Neutral is 0.5, evidence halves every 400 ticks, and the weights are capped at 16, matching sender scores. Twice the score scales the inherited generosity or aggression. `--no-lifetime-learning` keeps the genes and leaves the score at 0.5. Offspring start without these records. Synapses do not change.
- Pre-registered outcomes: a living donor compares their energy 100 ticks later with the energy just after the gift. Eating one's own kill is useful; reaching that spot after the corpse is gone is empty. A corpse the attacker never reaches adds nothing. A non-killing hit adds nothing. Recipient survival is not the training signal.
- Comparison freezes caution, generosity, and aggression at 1 and leaves hazards, seasons, scavenging, gifts, predation, and sender learning on. Five seeds, 2,000 ticks, range 12. Learning off/on: alive 0/0, births 1.4/1.4, gifts 4.2/4.4, attacks 5.2/5.2, hazard entries 1/1. Gift outcomes useful/empty 0/0 versus 1.2/2.4. Attack outcomes 0/0 versus 0.4/0.4. The off cell matches the all-frozen personality run. Exploratory. Empty gift outcomes were more common than useful ones in this sample.
- Validation: energy comparison, decay, a low score blocking a neutral attempt, eating a kill, a missed corpse, and an arrival after someone else ate. The gene does not change. The live checkbox is on. A founder reads 50/100 for both actions. The browser gift update matched the Python score.

### Neurotransmitter signs
- Joined the aggregate MaleCNS body table onto the 11 DNg13 neurons. The per-synapse table was not downloaded. Confidence threshold 0.5 was fixed to match the connectome release cut. Acetylcholine at or above that threshold keeps a positive weight. GABA would negate the outgoing weight. Glutamate edges are dropped. Monoamines would be recorded and left positive. Unclear or lower-confidence neurons stay positive. Ground truth in the table is recorded and is not the rule.
- In this extract, 10 neurons are acetylcholine with confidence above 0.9. Body 11670 (LT51) is glutamate, so its two outgoing edges are dropped. There is no GABA, so shuffling the applied signs does not change the controller.
- Held-out seeds 10–19, 500 ticks, selected decoder `turn_sign=-1`, `turn_gain=1`. All-positive mean food 4.0, the same per-seed counts as the decoder report. Signed and sign-shuffled both collected 4.1. Motors still move when the sensory input is on and stay at 0 when it is off. Exploratory interface result. The live ecosystem is unchanged.
- Validation: glutamate is dropped, low-confidence GABA stays positive, a negative weight cannot push activity below 0, the DNg13 shuffle matches the signed map, and the held-out runner repeats. The live page was not given a sign control.
