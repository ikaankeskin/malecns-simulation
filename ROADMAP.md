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
- HTML playback for one agent and a 10-fly one-shot contest with non-respawning pellets.

## Phase sequence

1. Persistent ecosystem (current): renewable food, age, death, corpses, metabolism, inspector.
2. Living environment: depletion, hazards, cycles — still no reproduction.
3. Life and death budgets: richer energy, causes of death.
4. Reproduction (after the world can persist or collapse on its own).
5. Genetics / mutation of **simulation parameters**, not connectome topology, unless a separate experimental mode is declared.
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
| Food spawn | Fixed patches, not random rain |
| Food availability | Lifecycle with cooldown; can deplete if eaten faster than growth |
| Perception | Nearest **mature** patch, limited sense range |
| Nutrition | Equal for every patch |
| Map | Finite, non-wrapping |
| Energy | Artificial budget: base drain + movement cost. Not fly metabolism |
| Death | Starvation or old age |
| Corpses | Visible, then decay. Not edible yet |
| Reproduction / LLM | Not in v0.1 |

## Next after v0.1

Reproduction, then inheritable decoder/metabolism parameters, then competition metrics. LLM cognition only after a non-LLM social baseline exists.
