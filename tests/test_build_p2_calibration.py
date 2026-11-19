"""P2 calibration builder targeted tests (zero model calls, dry-run only)."""
import unittest
import tools.build_p2_calibration as B
from tools.build_calibration_set import check_manifest_isolation


class BuildP2Tests(unittest.TestCase):
    def test_builds_18_cases_dry_run(self):
        built, feas = B.build_p2(dry_run=True)
        self.assertEqual(len(built), 18)
        self.assertTrue(all('SKIP' not in f[2] for f in feas))

    def test_splits(self):
        built, _ = B.build_p2(dry_run=True)
        from collections import Counter
        sp = Counter(x['manifest_case']['split'] for x in built)
        self.assertEqual(sp['development'], 6)
        self.assertEqual(sp['frozen_test'], 12)

    def test_all_with_gold(self):
        built, _ = B.build_p2(dry_run=True)
        self.assertTrue(all(x['manifest_case'].get('gold') for x in built))
        self.assertTrue(all(x['label']['gold_sha256'] for x in built))

    def test_isolation(self):
        built, _ = B.build_p2(dry_run=True)
        self.assertTrue(check_manifest_isolation([x['manifest_case'] for x in built]))

    def test_case_ids_unique_no_collision(self):
        built, _ = B.build_p2(dry_run=True)
        ids = [x['case_id'] for x in built]
        self.assertEqual(len(ids), len(set(ids)))
        import json
        from pathlib import Path
        orig = json.loads((B.ROOT / 'samples/calibration_manifest.json').read_text(encoding='utf-8'))
        orig_ids = {c['case_id'] for c in orig['cases']}
        self.assertFalse(set(ids) & orig_ids)

    def test_frozen_test_v2_templates(self):
        built, _ = B.build_p2(dry_run=True)
        test_templates = {x['manifest_case']['template'] for x in built if x['manifest_case']['split'] == 'frozen_test'}
        self.assertEqual(test_templates, {'nasa-voyager-news.candidate', 'w3c_accessibility_intro_zh'})

    def test_freeze_entries_deterministic(self):
        built, _ = B.build_p2(dry_run=True)
        from tools.build_calibration_set import dump
        manifest = {'judge_manifest_version': 1, 'cases': [x['manifest_case'] for x in built]}
        mb = dump(manifest).encode('utf-8')
        e1 = B._freeze_entries_p2(built, B.ROOT / 'samples', mb)
        e2 = B._freeze_entries_p2(built, B.ROOT / 'samples', mb)
        self.assertEqual(e1, e2)


if __name__ == '__main__':
    unittest.main()
