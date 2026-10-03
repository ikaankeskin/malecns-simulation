"""Observation boundary and engine-owned target resolution.

Only the immutable observation is supplied to a policy. The context retains
legacy target payloads for the executor; it must not be sent to model services.
The caller supplies edible targets after applying existing scavenging rules.
"""
import copy
import math
from dataclasses import dataclass
from .contracts import Candidate, Decision, Observation


@dataclass(frozen=True)
class TargetContext:
    observation: Observation
    _targets: tuple

    def resolve(self, decision):
        """Resolve only a decision for this agent and tick, returning an owned copy."""
        if not isinstance(decision, Decision):
            raise ValueError('Expected a typed Decision')
        if (decision.agent_id, decision.tick) != (self.observation.agent_id, self.observation.tick):
            raise ValueError('Decision belongs to another agent or tick')
        if decision.candidate_id is None:
            return None
        for candidate, target in zip(self.observation.candidates, self._targets):
            if candidate.id == decision.candidate_id:
                return copy.deepcopy(target)
        raise ValueError('Decision selected an unavailable candidate')


def prepare_targets(agent, direct, tick, sense_range, communication):
    """Build a local view without revealing hidden target positions or metadata.

    Memory locations come only from received reports, never refreshed from the
    world. Expiry is exclusive. Candidate order is the existing legacy tie order.
    No truncation: dropping an in-range candidate could change the legacy result.
    """
    candidates, targets = [], []
    if communication:
        for memory in agent.get('memories', []):
            if memory['until'] <= tick:
                continue
            targets.append(dict(memory, kind='following_signal'))
            candidates.append(Candidate(
                id=f'target:{len(candidates)}', kind='following_signal',
                x=memory['x'], y=memory['y'], evidence='received_report',
                observed_tick=memory['tick'], expires_tick=memory['until'],
                source=memory['source']))
    for target in direct:
        if math.hypot(agent['x']-target['x'], agent['y']-target['y']) >= sense_range:
            continue
        if target['kind'] not in ('foraging', 'scavenging'):
            raise ValueError('Unsupported direct target kind')
        targets.append(dict(target))
        candidates.append(Candidate(
            id=f'target:{len(candidates)}', kind=target['kind'],
            x=target['x'], y=target['y'], evidence='direct', observed_tick=tick))
    observation = Observation(
        agent_id=agent['id'], tick=tick, x=agent['x'], y=agent['y'],
        energy=agent.get('energy'), heading=agent.get('heading'), age=agent.get('age'),
        candidates=tuple(candidates))
    return TargetContext(observation, tuple(targets))
