# Artificial-life roadmap

Long-term vision: evolve this repository from a small foraging experiment into an inspectable artificial-life ecosystem.

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

## Next after lineages

Scavenging and seasonal food cycles are implemented. Next: measure survival and lineage outcomes across seeds with ecology enabled/disabled, then add a non-LLM social baseline and optional predation. LLM cognition follows the social baseline.

The live GitHub Pages app in `docs/` exposes agent count, food spawn rate, aging rate, reproduction rate, mutation rate, rule presets, and Randomize. It is a browser port of the Python ecosystem for inspection, not a second scientific engine.

