"""Synthetic Arrow fixtures test extraction logic, not biological performance."""
import tempfile
import unittest
from pathlib import Path
import pyarrow as pa
import pyarrow.feather as feather
from malecns_data import extract, verify_release


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.a = Path(self.tmp.name)/'annotations.feather'
        self.w = Path(self.tmp.name)/'weights.feather'
        self.nodes = [
            {'bodyId': i, 'type': typ, 'instance': str(i), 'somaSide': side, 'superclass': cls}
            for i, typ, side, cls in [(1,'DNg13','L','descending_neuron'),(2,'DNg13','R','descending_neuron'),(3,'A','L','visual_projection'),(4,'B','R','visual_projection'),(5,'C','L','cb_intrinsic'),(6,'D','L','visual_projection')]]
        self.edges = [(3,1,6),(4,2,8),(5,1,99),(6,1,6),(1,3,1),(3,4,2)]
        self.cfg = {'dataset':'male-cns:v1.0','output_type':'DNg13','input_superclass':'visual_projection','top_k_per_output':1,'min_selection_weight':5}
        self.write()

    def write(self):
        feather.write_feather(pa.Table.from_pylist(self.nodes), self.a)
        feather.write_feather(pa.table({k:[e[i] for e in self.edges] for i,k in enumerate(['body_pre','body_post','weight'])}),self.w)

    def test_selection_ties_induced_edges_and_provenance(self):
        g = extract(self.a,self.w,self.cfg)
        self.assertEqual([n['id'] for n in g['nodes']],['1','2','3','4'])
        self.assertEqual({(e['pre'],e['post'],e['weight']) for e in g['edges']},{('3','1',6),('4','2',8),('1','3',1),('3','4',2)})
        self.assertEqual(len(g['provenance']['sources']['weights']['sha256']),64)
        self.assertEqual(g,extract(self.a,self.w,self.cfg))

    def test_missing_bilateral_output_rejected(self):
        self.nodes[1]['somaSide']='L'; self.write()
        with self.assertRaisesRegex(ValueError,'exactly one L and one R'):
            extract(self.a,self.w,self.cfg)

    def test_empty_selection_rejected(self):
        self.cfg['min_selection_weight']=1000
        with self.assertRaisesRegex(ValueError,'No qualifying'):
            extract(self.a,self.w,self.cfg)

    def test_negative_retained_connection_rejected(self):
        self.edges.append((3,4,-2)); self.write()
        with self.assertRaisesRegex(ValueError,'positive'):
            extract(self.a,self.w,self.cfg)

    def test_synthetic_fixture_cannot_pass_release_verification(self):
        with self.assertRaisesRegex(ValueError,'SHA-256'):
            verify_release(extract(self.a,self.w,self.cfg))

    def test_wrong_schema_rejected(self):
        feather.write_feather(pa.table({'x':[1]}),self.w)
        with self.assertRaisesRegex(ValueError,'missing columns'):
            extract(self.a,self.w,self.cfg)


if __name__ == '__main__': unittest.main()
