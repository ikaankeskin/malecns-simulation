# Target decision interface v1

The first cognition milestone introduces a standard-library Python boundary between local target observations, policy choice, and engine side effects. It is an engineered interface, not a model of biological cognition. Open-Jev and generative LLM inference are not connected yet.

## Current scope

`social.select_target` now constructs a `TargetContext`, gives only its immutable `Observation` to a `TargetPolicy`, and resolves the returned `Decision`. The default `LegacyPolicy` chooses the nearest candidate. Memories precede directly sensed targets, preserving exact distance ties and report attribution. The existing follow-memory counters and events are applied after resolution, exactly once.

The contract currently covers food, edible corpses and remembered food reports. Corpse freshness and hungry-agent eligibility remain the caller's responsibility in `ecosystem.motors_for`. Hazard arbitration still runs afterward. Gifts, attacks, planting, exploratory drives, and extended-duration intentions are not part of this contract yet. No model can invoke those actions through this interface.

## Observation boundary

Frozen dataclasses hold self ID, tick, position, optional energy/heading/age, and a tuple of candidates. Each candidate supplies its kind, position, evidence source, observation tick, optional expiry and message source. These fields are explicitly copied; arbitrary agent dictionaries and target metadata never enter the policy observation.

Direct targets must be strictly inside sensory range. Report coordinates come from the recipient's stored memory; the observation builder does not query a hidden resource to refresh them. Expiry is exclusive. The normal tick loop already removes expired memories; the builder also excludes them for standalone callers. With communication off, no report candidates are exposed.

Candidate IDs are assigned after visibility filtering, so inserting invisible targets does not expose their count or change visible IDs. IDs are scoped to the current agent/tick context. They are not persistent resource IDs. No fixed top-k cut is applied to the legacy adapter because that could change behavior. A bounded model shortlist, current-target persistence and explicit observed-empty evidence require subsequent contract work.

## Policy and resolution

```python
from cognition.contracts import LEGACY_POLICY
from cognition.observation import prepare_targets

context = prepare_targets(agent, edible_targets, tick, sense_range=12,
                          communication=True)
decision = LEGACY_POLICY.choose(context.observation)
target = context.resolve(decision)
```

This example only selects and resolves a target. Use `social.select_target(..., policy=policy)` when the engine must also apply the existing memory-follow events. The policy receives no mutable agent or world reference. Choosing an eligible target does not move an agent: the existing sensory drive, circuit and movement integration still perform execution.

Resolution rejects untyped decisions, a different agent/tick, and unavailable candidate IDs. A null candidate means no selected target; it does not instantaneously zero recurrent activity. The returned dictionary is an owned copy. The context keeps private legacy payloads for execution and must never be serialized to a model service; serialize `dataclasses.asdict(context.observation)` instead.

This is a synchronous interface. Tick checks are not an asynchronous response protocol: a future scheduler must add request identity/candidate-set identity, revalidation at application time, deadlines, quotas and recorded fallback behavior. Dataclass type annotations are not an external JSON validator. No raw remote payload may be passed directly into this API.

## Validation and measured cost

Six synthetic tests cover visibility and metadata exclusion, immutable observations, report expiry, disabled communication, foreign/unknown decisions, stable ties, memory side effects, alternate-policy selection, and full trajectory comparison against the pre-adapter algorithm. The full suite has 120 passing tests, including existing browser parity checks.

The 50-agent/192-patch/1,200-tick DNg13 garden benchmark produced the same complete-output SHA-256 as before: `44d3c72f01c6c258b167cfe79fc47159ba1e7aa1377c2f0e305482bba00b4049`. This is software parity using a biological graph within artificial ecology, not biological validation. A single before/after timing was 3.058/3.563 seconds; the new observation allocation has a cost, and this pair is not a stable performance estimate. The future scheduler should construct model observations only at bounded decision points; keep profiling as that work proceeds.

Next: complete true world checkpoints and a resumable step API, the unfinished Phase A work in [the cognition plan](COGNITION_PLAN.md). Then add request-scoped decision recording/replay and a scheduler before external inference.
