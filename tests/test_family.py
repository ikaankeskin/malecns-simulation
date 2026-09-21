"""Synthetic pedigree checks. Parent links are the birth rule, not kinship behaviour."""
import unittest
from pathlib import Path
from ecosystem import family_tree, simulate_ecosystem
from view import ecosystem_document, render_viewer

DEMO = Path(__file__).resolve().parents[1] / 'demo.json'


def row(agent_id, generation, parents, birth=0, death=None, cause=None):
    return dict(id=agent_id, generation=generation, parents=parents, birth_tick=birth,
                death_tick=death, cause=cause)


class FamilyTreeTests(unittest.TestCase):
    def chain(self):
        return [
            row(0, 0, None), row(10, 0, None),
            row(1, 1, [0, 10], birth=1), row(11, 0, None),
            row(2, 2, [1, 11], birth=2), row(12, 0, None),
            row(3, 3, [2, 12], birth=3), row(13, 0, None),
            row(4, 4, [3, 13], birth=4),
            row(5, 5, [4, 14], birth=5), row(14, 0, None),
            row(30, 3, [2, 12], birth=3),
        ]

    def test_depth_cap_omits_further_kin_not_siblings(self):
        tree = family_tree(self.chain(), 3, 100, max_depth=1)
        self.assertEqual([node['id'] for node in tree['nodes']], [2, 12, 3, 4])
        self.assertEqual([node['relation'] for node in tree['nodes']],
                         ['ancestor', 'ancestor', 'self', 'descendant'])
        self.assertEqual(tree['omitted'], 5)
        self.assertTrue(all(node['id'] != 30 for node in tree['nodes']))
        self.assertEqual(family_tree(self.chain(), 3, 100, max_depth=1), tree)

    def test_unborn_and_dead_are_labelled_from_the_tick(self):
        rows = self.chain()
        rows[8] = row(4, 4, [3, 13], birth=4, death=50, cause='starvation')
        early = family_tree(rows, 3, 3, max_depth=1)
        self.assertEqual([node['id'] for node in early['nodes']], [2, 12, 3])
        self.assertEqual(early['omitted'], 4)
        dead = family_tree(rows, 4, 50, max_depth=0)
        self.assertFalse(dead['nodes'][0]['alive'])
        self.assertEqual(dead['nodes'][0]['cause'], 'starvation')
        self.assertTrue(family_tree(rows, 4, 49, max_depth=0)['nodes'][0]['alive'])
        self.assertEqual(family_tree(rows, 5, 4, max_depth=1)['nodes'], [])
        with self.assertRaises(ValueError):
            family_tree(rows, 3, 100, max_depth=-1)

    def test_playback_roster_includes_both_parents(self):
        kwargs = dict(
            agents=4, patches=1, map_half=8, disconnected=True,
            min_repro_age=1, min_repro_energy=0.2, mate_radius=40, repro_cooldown=3,
            repro_cost=0.05, max_age=500, base_drain=0.0001, move_cost=0.0,
            max_population=6, energy_start=1.0, record_every=12)
        born = simulate_ecosystem(DEMO, 12, 1, **kwargs)
        child = next(row for row in born['roster'] if row['parents'])
        tree = family_tree(born['roster'], child['id'], 11)
        shown = {node['id'] for node in tree['nodes']}
        self.assertTrue(set(child['parents']).issubset(shown))
        payload = ecosystem_document(DEMO, 12, 1, **kwargs)
        self.assertEqual(payload['roster'], born['roster'])
        html = render_viewer(payload)
        self.assertIn('id="family-tree"', html)
        self.assertIn('function familyTree', html)
