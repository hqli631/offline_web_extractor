"""P2 blind kit builder targeted tests (zero model calls)."""
import json
import tempfile
import unittest
from pathlib import Path
import tools.build_p2_review_kit as K
from tools.build_calibration_set import ROOT


class KitTests(unittest.TestCase):
    def test_case_row_with_gold(self):
        man = json.loads((ROOT / 'samples/p2_manifest.json').read_text(encoding='utf-8'))
        mc = man['cases'][0]
        row = K._case_row(mc, ROOT / 'samples')
        self.assertIn(row['case_meta']['mode'], ('with_gold', 'source_only'))
        self.assertIn('source', row['report']['prompt'])
        self.assertIn('candidate', row['report']['prompt'])

    def test_build_kit_no_leak(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'kit'
            rc = K.main(['--output', str(out)])
            self.assertEqual(rc, 0)
            packets = list((out / 'packets').glob('*.md'))
            self.assertEqual(len(packets), 18)
            mapping = json.loads((out / 'sealed_mapping.json').read_text(encoding='utf-8'))
            for p in packets:
                txt = p.read_text(encoding='utf-8')
                for cid in mapping.values():
                    self.assertNotIn(cid, txt)
            tmpl = json.loads((out / 'human_labels.blind.json').read_text(encoding='utf-8'))
            self.assertEqual(len(tmpl['cases']), 18)

    def test_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'kit'
            out.mkdir()
            rc = K.main(['--output', str(out)])
            self.assertEqual(rc, 3)


if __name__ == '__main__':
    unittest.main()
