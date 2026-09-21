# Next phases

Detailed plan for the remaining artificial-life work. Each item names a mechanism that can be implemented on the current CPU ecosystem, the projects it is drawn from, what this repository should copy, and what it must not claim.

MaleCNS-derived circuits stay the tick-level locomotion controller. New behaviour is a simulation abstraction unless a checked-in comparison says otherwise. One mechanism per commit, with an on/off baseline in the style of `social_experiment.py`. Python is the scientific engine; the browser page is an inspector and must match any rule that the live controls expose.

LLM cognition is out of this plan. It stays behind a non-LLM social baseline.

## Order

Later items depend on earlier death labels, actions, or measurements. Do not combine two new mechanisms in one ablation.

1. Ecology comparison — measure the world that already exists.
2. Family trees — show parent links that births already record.
3. Map hazards and richer causes of death — one new environmental damage rule and explicit death labels.
4. Costly cooperation — one optional energy gift, default off in the baseline.
5. Optional predation — one optional attack, default off.
6. Personality — inherited multipliers for actions that exist by then.
7. Lifetime learning beyond sender scores — individual, non-inherited outcome scores for those actions.
8. Neurotransmitter signs — a separate controller experiment. Do not run it in the same comparison as a world-rule change.

## 1. Ecology comparison

**Already true.** Seasons scale plant timers. Hungry agents can scavenge fresh corpses. Uneaten corpses can fertilize one nearby immature patch. `--no-seasons` and `--no-scavenging` exist. There is no paired multi-seed report.

**What to copy.** `social_experiment.py`: same graph hash, decoder (`turn_sign=-1`, `turn_gain=1`), seeds, tick count, and a written caveat that trajectories diverge and results are exploratory. Avida-style work on ecology and phylogeny (Dolson and colleagues; the 2024 ecology/phylogeny simulations) is the reason to record lineage outcomes, not only final headcount. Those studies show that resource regime and spatial structure change tree shape. This comparison should therefore report living founders and births, not a phylogenetic index yet.

**Implement.** A 2×2 on seeds 0–4, 2,000 ticks, sensory range 12: seasons on/off × scavenging on/off. Composting stays available when scavenging is off, matching the current rule. Record per seed: final alive, births, peak population, plant meals, scavenged meals, and how many founder lineages still have a living descendant. Check in the JSON under `docs/`. No new world rule.

**Do not claim.** That seasons or scavenging improve survival. Five seeds are a smoke comparison. Python and browser random generators differ, so this report does not validate the live page.

## 2. Family trees

**Already true.** Each birth stores both parent IDs, generation, and founder lineage. The dashboard counts living descendants per founder. It does not draw the parent–child graph or attach a cause of death to a dead node.

**What to copy.** Avida tracks phylogeny at individual level or genotype level and warns that the two summaries disagree (Ofria and Wilke; Dolson’s individual-tracking fork; ALife standard phylogeny JSON). This world has two parents and a small population cap, so the right object is an individual pedigree, not a species tree and not a Newick file. Polyworld and Neural MMO do not add a better tree design than that.

**Implement.** From the event log, build the ancestor and descendant graph of the selected agent: id, generation, alive or cause of death, and parent links. Cap the drawn depth so a long run stays readable, and keep a count of omitted nodes. Python playback and the live inspector show the same graph. A later ecology report may add one simple shape number (mean generations from founder to living leaves). No external tree library.

**Do not claim.** Relatedness, kinship preference, or speciation. The tree is a record of the birth rule.

## 3. Map hazards and richer causes of death

**Already true.** Death is `starvation` or `old_age`. Energy is one pool: base drain plus movement, restored by plants and freshness-scaled corpses. The map is finite and reflecting. There is no terrain damage.

**What to copy.** Neural MMO separates traversable terrain from hazards and names starvation as health loss after a resource hits zero, with combat as a different cause (Suarez et al., 2019 and the later platform paper). Polyworld puts organisms in a world that can kill them through energy loss, fighting, and aging, and keeps physiology simple. Neither design should be imported whole. Neural MMO’s food, water, and health bars, fog ring, and three combat styles would confound every existing energy result. Polyworld’s evolving network topology conflicts with the fixed MaleCNS circuit.

**Implement.** One seeded hazard field: a small number of discs, stable for the run, inside the finite map. Standing in a disc drains a fixed energy cost per tick, distinct from metabolism. Within sensory range, a hazard is a repulsive candidate that competes with food and remembered locations; the circuit still only receives a directional sensory value and still only outputs locomotion. Death causes, first match in this order if several would apply on the same tick: `predation`, `hazard`, `starvation`, `old_age`. Predation is reserved until that phase; until then it cannot occur. Add `--no-hazards`. The inspector shows the cause on the corpse and on the family-tree node.

Keep a single energy pool. A second health bar is a later experiment, because it would rewrite meal, metabolism, and lifespan results.

**Comparison.** Same seeds and decoder as the ecology report: hazards off versus on, seasons and scavenging left at their defaults. Report alive, births, deaths by cause, and meals. Exploratory only.

**Do not claim.** Injury, disease, temperature physiology, or that the DNg13 circuit evolved to avoid danger. Avoidance, if it appears, is an interface outcome.

## 4. Costly cooperation

**Already true.** Agents can emit a local food report that costs 0.01 energy. Receivers learn a decaying usefulness score for each sender. There is no transfer of resources, no shared reward, and no alliance.

**What to copy.** Melting Pot (Leibo et al., 2021; Agapiou et al., 2022) separates the physical rules (the substrate) from the agents, and scores mixed-motive games such as public-good cleanup and commons harvest against a background population. The useful part is the evaluation habit: one costly social action, an off baseline, and no claim from a single training run. The MARL stack, grid substrates, and held-out partner populations are out of scope. Polyworld lets organisms evolve whether to fight or tolerate neighbours, but it does not implement a gift. Costly signalling theory is a reason to make the action expensive, not a model to code.

**Action.** A directed gift. A living agent may give a fixed energy quantum to one neighbour inside a short range, on a cooldown. The recipient gains less than the donor pays (a transfer loss). The action is optional and default-off in the paired comparison, so current communication numbers stay interpretable. An inherited `generosity` multiplier, added in the personality phase, may later change how often the gift is attempted. Until that gene exists, use a fixed probability so the action can be ablated alone. A public-good patch is not part of this baseline.

Track gifts sent, gifts received, energy moved, and whether the recipient is alive 100 ticks later. That last count is an observation, not proof the gift saved them.

**Comparison.** Communication and sender learning held at the current defaults. Gift off versus on. Same seeds, ticks, and decoder. Do not call a higher alive-count cooperation, trust, or friendship.

## 5. Optional predation

**Already true.** Fresh corpses are food. Agents do not damage each other.

**What to copy.** Polyworld’s fight is the closest small design: an attack action spends energy, removes energy from a neighbour, and a killed body can be eaten. Neural MMO’s style triangle and loot tables are game systems, not needed here. EcoSim-style speciation is explicitly not a goal while every agent keeps the same connectome.

**Action.** Default off. An attack has a range shorter than sensory range, an energy cost, a cooldown, and a fixed damage to the target’s energy. If that damage kills, the cause is `predation` and the corpse follows the existing scavenging rules. The attacker does not automatically receive the meal; it has to reach the corpse like any scavenger. No damage types, no knockback, no territory. A non-lethal energy contest is not part of this phase.

The circuit does not gain an attack output. Attempting an attack is a simulation policy, initially a fixed probability when a neighbour is closer than food and the attacker’s energy is above a floor. Personality and lifetime learning may scale that probability later. `--no-predation` is the baseline.

**Comparison.** Hazards, seasons, scavenging, gifts, and learning fixed. Predation off versus on. Report deaths by cause, scavenged meals, alive, and births. A world of only predators is an acceptable negative result.

## 6. Personality

**Already true.** Offspring inherit and mutate turn, sensory gain, metabolism, speed, lifespan, fertility, signalling, and responsiveness. `spot`, `echo`, and `drift` are weak quirks. Learned sender scores are not inherited. Nothing in the genome is a personality inventory.

**What to copy.** Polyworld encodes physiology and behavioural bias in the genome and lets lifetime Hebbian change sit on top. That split matches this repo: genes are inherited simulation multipliers; lifetime scores are individual state. Big Five and other psychometric inventories do not map onto a fly circuit or onto this action set, so they are not implemented.

**Implement.** Add genes only for actions that exist, each with a stated mechanical effect and a bound like the current `GENE_BOUNDS`:

| Gene | Effect | Waits until |
|---|---|---|
| `caution` | Scales how strongly a sensed hazard repels, relative to food | Hazards |
| `generosity` | Scales the probability of attempting a gift | Cooperation |
| `aggression` | Scales the probability of attempting an attack | Predation |

Leave `spot`, `echo`, and `drift` as nearly neutral markers so older runs stay readable. Do not rename them into personality. Offspring blend and mutate the new genes the same way as signalling. The inspector shows the three values. They are tendencies, not traits of character.

**Comparison.** One gene at a time, variation on versus the gene frozen at its neutral value, other new actions left on. Report the action rate (gifts, attacks, hazard entries) beside alive and births, so a survival change can be read against what the gene actually did.

## 7. Lifetime learning beyond sender scores

**Already true.** Each agent keeps at most eight sender records. Meals and empty arrivals move a decaying score. Expired trips do not. The score only scales whether a new report is remembered. It is not inherited and it does not change synapses.

**What to copy.** The Baldwin effect (Hinton and Nowlan, 1987, and later foraging models) is the reason to keep learned state off the genome: lifetime adjustment can change who reproduces without writing the lesson into the offspring. Reward-modulated Hebbian rules (Miconi, 2021, and the embodied-control literature) can change weights on a fixed topology, but they are a poor first step on an 11-neuron rate model that has no task reward and no saturation audit. PLAN.md already requires a plasticity rule to wait until fixed-circuit controls are measured, and to track saturation. Sender scores are the pattern to extend: local evidence, decay, a cap, an off switch.

**Implement.** For each new action the agent actually attempts, keep a small individual table: gift outcomes and attack outcomes, same decay and cap style as sender scores. A gift’s evidence is whether the donor’s energy is higher or lower after a fixed window than donors who did not give, or a simpler pre-registered proxy stated in the experiment file before the run. An attack’s evidence is whether the attacker eats that corpse. The score scales the inherited generosity or aggression when choosing the next attempt. Existing memories, locomotion, topology, and genomes stay fixed. `--no-lifetime-learning` keeps the genes but freezes these tables at the neutral prior.

Synaptic plasticity is a later milestone, not part of this item. If it is added afterwards, it is a bounded gain on existing DNg13 weights, reset each birth, with an on/off comparison and a saturation metric. It is not connectome learning.

**Do not claim.** Honesty, reciprocity, friendship, or dopamine. Another agent can consume a reported patch, or a corpse, before the learner arrives. The update must not use hidden ground truth.

## 8. Neurotransmitter signs

**Already true.** The controller is an all-excitatory rate model. Synapse counts are positive weights. Provenance already says no transmitter signs are inferred from wiring. The DNg13 extract has 11 neurons and 32 connections.

**What the data supports.** MaleCNS v1.0 publishes aggregate predictions in `body-neurotransmitters-male-cns-v1.0.feather` (about 42 MB) and per-synapse probabilities in a 2.7 GB table. Use the aggregate only. Eckstein et al. (Cell, 2024) predict acetylcholine, glutamate, GABA, serotonin, dopamine, and octopamine from electron microscopy; neuron-level accuracy on the brain datasets they tested is about 94%, with lower confidence on some classes. MaleCNS applies the same style of prediction. Acetylcholine is the usual fast excitatory transmitter and GABA the usual fast inhibitory transmitter. Glutamate has no single sign in the fly central nervous system: it can excite or inhibit depending on the receptor, which this wiring extract does not contain. Monoamines are modulatory, not a plus or minus on a rate synapse. A public mirror of the MaleCNS table shows that most bodies are labelled `unclear`; a sign applied to an unclear neuron would be an invention.

**Policy.** Join consensus transmitter and confidence onto the existing 11 DNg13 neurons. Do not download the 2.7 GB synapse table. Sign rule, applied as a weight multiplier and recorded in provenance:

- acetylcholine, at or above a pre-registered confidence: `+1`
- GABA, at or above that confidence: `-1`
- glutamate: `0` (dropped) until a receptor source exists
- dopamine, octopamine, serotonin, histamine: recorded, not applied
- `unclear` or below confidence: leave the current positive weight and list the neuron as unsigned

Compare three controllers on the existing held-out foraging seeds: all-positive weights, signed weights, and a sign-shuffled control. Report collection and whether outputs still move when the input is on. A foraging change is an interface result, not evidence that DNg13 encodes food or inhibition in the animal. Glutamate stays unsigned, and monoamines are recorded but not applied.

## Validation habit

Match the social experiments: deterministic unit tests for the rule, Python/JavaScript parity when the live page exposes it, then one checked-in paired-seed JSON with the circuit hash and a caveat. Fixture tests stay labelled as fixtures. No biological-fidelity claim is attached to a passing test.

## Sources

- MaleCNS v1.0 downloads, including `body-neurotransmitters-male-cns-v1.0.feather`: https://male-cns.janelia.org/download/
- Eckstein et al., 2024, Cell. Neurotransmitter classification from electron microscopy images at synaptic sites in Drosophila. https://doi.org/10.1016/j.cell.2024.03.016
- Yaeger, 1994. Polyworld. Artificial Life III.
- Leibo et al., 2021. Melting Pot. ICML. https://proceedings.mlr.press/v139/leibo21a.html
- Agapiou et al., 2022. Melting Pot 2.0. https://arxiv.org/abs/2211.13746
- Suarez et al., 2019. Neural MMO. https://arxiv.org/abs/1903.00784
- Ofria and Wilke, 2004. Avida. Artificial Life 10:191–229.
- Hinton and Nowlan, 1987. How learning can guide evolution. Complex Systems 1:495–502.
- Miconi, 2021. Learning to acquire novel cognitive tasks with evolution, plasticity and meta-meta-learning. https://arxiv.org/abs/2112.08588
