"""Sign-rule checks. The DNg13 rows are a joined table, not a synthetic fixture."""
import json
import unittest
from pathlib import Path
from neurotransmitter import assignments, decision_for, load_table, multipliers, shuffle_multipliers
from neurotransmitter_experiment import compare
from sim import Circuit

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / 'circuits' / 'dng13.json'
TABLE = ROOT / 'circuits' / 'dng13-neurotransmitters.json'


class NeurotransmitterTests(unittest.TestCase):
    def test_rule_drops_glutamate_and_leaves_monoamines_positive(self):
        self.assertEqual(decision_for('glutamate', 0.99)['multiplier'], 0)
        self.assertEqual(decision_for('GABA', 0.5)['multiplier'], -1)
        self.assertEqual(decision_for('gaba', 0.49)['decision'], 'unsigned')
        self.assertEqual(decision_for('acetylcholine', 0.5)['multiplier'], 1)
        self.assertEqual(decision_for('dopamine', 0.99)['reason'], 'monoamine')
        self.assertEqual(decision_for('unclear', 0.99)['multiplier'], 1)
        self.assertEqual(decision_for(None, None)['decision'], 'unsigned')

    def test_dng13_table_drops_only_the_glutamate_input(self):
        graph = json.loads(GRAPH.read_text())
        rows = assignments(load_table(TABLE), [node['id'] for node in graph['nodes']])
        by_id = {row['id']: row for row in rows}
        self.assertEqual(by_id['11670']['consensus_nt'], 'glutamate')
        self.assertEqual(by_id['11670']['multiplier'], 0)
        self.assertTrue(all(row['multiplier'] == 1 and row['decision'] == 'excitatory'
                            for row in rows if row['id'] != '11670'))
        self.assertNotIn('inhibitory', {row['decision'] for row in rows})
        signed = multipliers(rows)
        self.assertEqual(shuffle_multipliers(rows, 0), signed)
        plain = Circuit(graph)
        dropped = Circuit(graph, signs=signed)
        self.assertEqual(sum(len(incoming) for incoming in dropped.incoming),
                         sum(len(incoming) for incoming in plain.incoming) - 2)
        flipped = dict(signed)
        flipped['12014'] = -1
        negative = Circuit(graph, signs=flipped)
        weights = [weight for incoming in negative.incoming for _, weight in incoming]
        self.assertTrue(any(weight < 0 for weight in weights))
        self.assertTrue(all(0 <= value <= 1 for value in negative.step([0.5] * len(negative.nodes))))

    def test_shuffled_signs_keep_the_same_counts(self):
        rows = [
            {'id': 'a', 'decision': 'excitatory', 'multiplier': 1},
            {'id': 'b', 'decision': 'inhibitory', 'multiplier': -1},
            {'id': 'c', 'decision': 'dropped', 'multiplier': 0},
            {'id': 'd', 'decision': 'unsigned', 'multiplier': 1},
        ]
        shuffled = shuffle_multipliers(rows, 1)
        self.assertEqual(shuffled['c'], 0)
        self.assertEqual(shuffled['d'], 1)
        self.assertEqual(sorted(shuffled[key] for key in ('a', 'b')), [-1, 1])

    def test_held_out_comparison_is_repeatable(self):
        first = compare(GRAPH, ticks=40, seeds=[10])
        self.assertEqual(first, compare(GRAPH, ticks=40, seeds=[10]))
        self.assertTrue(first['shuffle_identical_to_signed'])
        self.assertEqual(first['edges_dropped'], 2)
        self.assertTrue(first['conditions']['all_positive']['moves_when_input_is_on'])
        with self.assertRaises(ValueError):
            compare(GRAPH, ticks=40, seeds=[10, 10])
