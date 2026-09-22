# Artificial-life roadmap

Long-term vision: evolve this repository from a small foraging experiment into an inspectable artificial-life ecosystem.

## Game direction: become the riverkeeper

The player shapes habitat while autonomous agents live with the consequences. The first implemented interaction is a finite watering reserve for gardens, with seasonal water, moisture inspection and slower playback. This is a sandbox, not yet a balanced game.

Implemented: **survive the first drought**, a fixed-seed introductory mission with a paused start, weather countdown, finite reserve, intervention history, terminal result and same-world retry. It requires 8 survivors and 3 separate garden cells at least 20% moist at tick 1,200. It tests end-of-drought reserve timing; it does not require maintaining crops throughout the drought. Baseline and winning intervention are reproducible in `tests/mission.cjs`.

Next priority: playtest the tutorial, then replace the finish-line moisture target with sustained garden productivity in a second mission. Tune nutrient and water constraints together so irrigation has a measurable effect on growth and meals. Add an alert before drought and a clearer garden-selection view before introducing more tools. Save/load and replayable action logs remain unimplemented.

Then add choices that compete for the same resources:

1. **Cisterns versus channels:** store rain for later or divert some river supply now. Each should have a build cost and a downstream consequence; unlimited water would erase the choice.
2. **Living legacy:** pin and name a lineage or ancestral garden, receive a few meaningful event notifications, and take on optional rescue goals. Attachment should make losses and recoveries matter.
3. **Wetlands and crossings:** create fertile floodplains with flood risk, then bridges or routes that make river geography affect movement. This requires explicit movement constraints and flood mechanics first.
4. **Progression through scenarios:** unlock tools through distinct maps and objectives, with save/load and reproducible player-action logs before longer campaigns.

Keep the neural inspector as an optional layer for curious players. The main screen should answer: what is threatened, what can I do, what will it cost, and did it help? More population counters alone will not provide that loop.

Soil follow-on implemented: shared local nutrient limits, proportional growth allocation, slow recovery, corpse nutrient returns, fertility overlay and garden soil history. Controlled results: `docs/soil-comparison.json`. Migration remains an open experimental question; nutrient diffusion, calibration and explicit movement/occupancy metrics are not implemented.

Latest extension: large maps and persistent gardens. Agents carry one seed, spend energy to plant, and leave food sources that can feed descendants after the planter dies. Patch history and an on/off comparison are implemented. The subsequent soil mode adds depletion and recovery; its replenishment still represents an external environmental input.

**Design principle:** MaleCNS-derived circuits control embodied, immediate behaviour. Higher-level systems may later add memory, communication, and strategic intent. Every mechanism is labelled as measured biology or a simulation abstraction.

```
WORLD → sensory environment → MaleCNS-derived circuits → body
      → internal state (energy, age, health)
      → optional higher-level agent layer
      → ACTION → WORLD
```

Do not claim that food-seeking, survival, social behaviour, or evolution are properties of the biological connectome unless a specific experiment supports that claim.

## What is already built

- Synthetic foraging loop and official MaleCNS v1.0 DNg13 extract.
- Toy rate controller; decoder signs/gains are experimental interface parameters.
- HTML playback for one agent, a 10-fly contest, and a persistent ecosystem with births.

## Phase sequence

1. Persistent ecosystem: renewable food, age, death, corpses, metabolism, inspector.
2. Living environment: depletion, hazards, cycles.
3. Life and death budgets: richer energy, causes of death.
4. Reproduction: proximity, energy cost, parent IDs, generations.
5. Genetics / mutation of **simulation parameters** (current): turn gain, sensory gain, metabolism, speed. Connectome topology stays fixed unless a separate experimental mode is declared.
6. Resource competition metrics.
7. Corpses as food, then optional predation.
8–10. Relationships, collaboration actions, minimal signalling.
11–14. Optional slow LLM layer, bounded memory, personality, lifetime learning — MaleCNS stays the tick-level body controller.
15. Observatory viewer: charts, timeline, family trees.

Suggested later layout (gradual, not a rewrite): `simulation/`, `agents/`, `controllers/`, `viewer/`, `experiments/`. Keep a CPU path.

## Ecosystem v0.1 decisions

These are simulation abstractions unless noted.

| Question | v0.1 choice |
|---|---|
| Agent identity | Artificial organisms with a MaleCNS-derived **controller**, not reconstructed flies |
| MaleCNS topology | Fixed for every agent |
| Food spawn | Random relocation after each cooldown, not fixed patches |
| Food availability | Lifecycle with cooldown; can deplete if eaten faster than growth |
| Perception | Nearest mature patch or, when hungry, fresh corpse; limited sense range |
| Nutrition | Equal for every patch |
| Map | Finite, non-wrapping |
| Energy | Artificial budget: base drain + movement cost. Not fly metabolism |
| Death | Starvation or old age |
| Corpses | Freshness-scaled scavenging; uneaten remains can fertilize one nearby immature patch |
| Reproduction | Two-parent proximity, energy cost, population cap. Same controller topology |
| Evolution | Inherit and mutate simulation multipliers. Not connectome evolution |

## Next phases

Signalling, bounded location memory, and per-sender usefulness are implemented. Seasons and scavenging are implemented. The ordered plan for what remains is [docs/NEXT_PHASES.md](docs/NEXT_PHASES.md):

1. Ecology on/off comparison across seeds. Done: `docs/ecology-comparison.json`.
2. Family trees from parent IDs already stored at birth. Done in the inspector and playback.
3. Map hazards, with death causes beyond starvation and old age. Done: `docs/hazard-comparison.json`.
4. One costly cooperation action, with an off baseline. Done: `docs/gift-comparison.json`.
5. Optional predation, default off. Done: `docs/predation-comparison.json`.
6. Inherited personality multipliers for those actions. Done: `docs/personality-comparison.json`.
7. Lifetime learning of action outcomes, without changing synapses or inheriting the scores. Done: `docs/lifetime-comparison.json`.
8. Neurotransmitter signs from MaleCNS predictions, as a separate controller comparison. Done: `docs/neurotransmitter-comparison.json`.

Alliances and LLM cognition stay out of that plan. Learned usefulness is not honesty or friendship.

Follow-on implemented: memory of received energy and optional preference for past helpers, with visible transfers and a paired recipient-policy comparison (`docs/reciprocity-comparison.json`). This adds individual relationship history, not alliances or an LLM.

The live GitHub Pages app in `docs/` exposes agent count, food spawn rate, aging rate, reproduction rate, mutation rate, rule presets, and Randomize. It is a browser port of the Python ecosystem for inspection, not a second scientific engine.
