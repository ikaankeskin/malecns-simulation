"""Presynaptic sign rule for the aggregate MaleCNS transmitter table.

The threshold is 0.5, chosen to match the connectome release cut before the
eleven DNg13 rows were joined. Consensus transmitter and predicted confidence
are the only columns that change a weight. Glutamate is dropped. Monoamines
are recorded and stay positive. Unclear or low-confidence neurons stay positive.
"""
import json
import random
from pathlib import Path


CONFIDENCE_THRESHOLD = 0.5
MONOAMINES = frozenset({'dopamine', 'octopamine', 'serotonin', 'histamine'})
APPLIED = frozenset({'excitatory', 'inhibitory'})


def decision_for(consensus, confidence, threshold=CONFIDENCE_THRESHOLD):
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
        raise ValueError('confidence threshold must be between 0 and 1')
    name = '' if consensus is None else str(consensus).strip().lower()
    if isinstance(confidence, bool) or (confidence is not None and not isinstance(confidence, (int, float))):
        raise ValueError('confidence must be a number or null')
    if name == 'glutamate':
        return {'decision': 'dropped', 'multiplier': 0, 'reason': 'glutamate'}
    if name in MONOAMINES:
        return {'decision': 'unsigned', 'multiplier': 1, 'reason': 'monoamine'}
    if confidence is not None and confidence >= threshold and name == 'acetylcholine':
        return {'decision': 'excitatory', 'multiplier': 1, 'reason': 'acetylcholine'}
    if confidence is not None and confidence >= threshold and name == 'gaba':
        return {'decision': 'inhibitory', 'multiplier': -1, 'reason': 'gaba'}
    return {'decision': 'unsigned', 'multiplier': 1, 'reason': 'unclear_or_below_confidence'}


def load_table(path):
    table = json.loads(Path(path).read_text())
    neurons = table.get('neurons')
    if not isinstance(neurons, list) or not neurons:
        raise ValueError('neurotransmitter table needs a neurons list')
    seen = set()
    for row in neurons:
        body = str(row.get('body', ''))
        if not body or body in seen:
            raise ValueError('neurotransmitter body ids must be unique')
        seen.add(body)
        if 'consensus_nt' not in row or 'predicted_nt_confidence' not in row:
            raise ValueError('neurotransmitter rows need consensus_nt and predicted_nt_confidence')
    return table


def assignments(table, node_ids, threshold=CONFIDENCE_THRESHOLD):
    by_id = {str(row['body']): row for row in table['neurons']}
    rows = []
    for node_id in node_ids:
        source = by_id.get(str(node_id))
        if source is None:
            chosen = decision_for(None, None, threshold)
            record = {'id': str(node_id), 'consensus_nt': None, 'confidence': None,
                      'predicted_nt': None, 'ground_truth': None}
        else:
            chosen = decision_for(source.get('consensus_nt'), source.get('predicted_nt_confidence'), threshold)
            record = {
                'id': str(node_id),
                'consensus_nt': source.get('consensus_nt'),
                'confidence': source.get('predicted_nt_confidence'),
                'predicted_nt': source.get('predicted_nt'),
                'ground_truth': source.get('ground_truth'),
            }
        record.update(chosen)
        rows.append(record)
    return rows


def multipliers(rows):
    return {row['id']: row['multiplier'] for row in rows}


def shuffle_multipliers(rows, seed):
    """Permute applied +1 and -1 signs. Dropped and unsigned neurons stay put."""
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError('shuffle seed must be an integer')
    result = multipliers(rows)
    applied = [row for row in rows if row['decision'] in APPLIED]
    values = [row['multiplier'] for row in applied]
    random.Random(seed).shuffle(values)
    for row, value in zip(applied, values):
        result[row['id']] = value
    return result
