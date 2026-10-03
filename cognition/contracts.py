"""Immutable, allowlisted inputs for target selection. Standard library only."""
from dataclasses import dataclass
import math
from typing import Optional, Protocol, Tuple


@dataclass(frozen=True)
class Candidate:
    # IDs are local to one observation; they are not persistent world IDs.
    id: str
    kind: str
    x: float
    y: float
    evidence: str
    observed_tick: int
    expires_tick: Optional[int] = None
    source: Optional[int] = None


@dataclass(frozen=True)
class Observation:
    agent_id: int
    tick: int
    x: float
    y: float
    energy: Optional[float]
    heading: Optional[float]
    age: Optional[int]
    candidates: Tuple[Candidate, ...]
    version: int = 1


@dataclass(frozen=True)
class Decision:
    agent_id: int
    tick: int
    candidate_id: Optional[str]


class TargetPolicy(Protocol):
    def choose(self, observation: Observation) -> Decision:
        ...


class LegacyPolicy:
    """Nearest target; tuple order preserves memory-first and direct tie order."""

    def choose(self, observation: Observation) -> Decision:
        selected = min(observation.candidates,
                       key=lambda c: math.hypot(observation.x-c.x, observation.y-c.y),
                       default=None)
        return Decision(observation.agent_id, observation.tick,
                        selected.id if selected else None)


LEGACY_POLICY = LegacyPolicy()
