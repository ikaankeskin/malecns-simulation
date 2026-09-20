"""Synthetic-only tests for the HTML playback viewer."""
import json
import tempfile
import unittest
from pathlib import Path
from view import circuit_kind, playback_document, render_viewer, write_viewer

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / 'demo.json'
DNG13 = ROOT / 'circuits' / 'dng13.json'


class ViewerTests(unittest.TestCase):
    def test_demo_payload_is_labelled_synthetic_and_has_activity(self):
        payload = playback_document(DEMO, 20, 4)
        self.assertEqual(payload['kind'], 'synthetic')
        self.assertIn('NOT MaleCNS', payload['source'])
        self.assertEqual(len(payload['ticks']), 20)
        self.assertEqual(len(payload['nodes']), 6)
        self.assertEqual(len(payload['ticks'][0]['activity']), 6)
        self.assertEqual(payload['decoder']['turn_sign'], 1)

    def test_dng13_payload_is_labelled_derived_not_synthetic(self):
        payload = playback_document(DNG13, 5, 4, turn_sign=-1, turn_gain=1)
        self.assertEqual(payload['kind'], 'malecns-derived')
        self.assertNotEqual(payload['kind'], 'synthetic')
        self.assertEqual(payload['decoder']['turn_sign'], -1)
        self.assertEqual(len(payload['ticks'][0]['activity']), len(payload['nodes']))

    def test_html_embeds_json_and_controls(self):
        payload = playback_document(DEMO, 8, 4)
        html = render_viewer(payload)
        self.assertEqual(html.count('__PLAYBACK_JSON__'), 0)
        self.assertIn('id="play"', html)
        self.assertIn('id="reset"', html)
        self.assertIn('id="forward"', html)
        start = html.index('id="playback">') + len('id="playback">')
        end = html.index('</script>', start)
        embedded = json.loads(html[start:end])
        self.assertEqual(embedded['kind'], 'synthetic')
        self.assertEqual(len(embedded['ticks']), 8)
        self.assertNotIn("raw ===", html)

    def test_write_viewer_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'view.html'
            write_viewer(DEMO, 6, 4, path)
            text = path.read_text()
        self.assertIn('synthetic', text)
        self.assertIn('Play', text)

    def test_unverified_kind(self):
        self.assertEqual(circuit_kind({'source': 'User-supplied CSV; biological provenance unverified'}),
                         'unverified')


if __name__ == '__main__':
    unittest.main()
