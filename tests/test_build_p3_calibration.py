# -*- coding: utf-8 -*-
"""Artifact tests for P3 v3 build (freeze v7 + manifest + blind kit inputs)."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.score_judge_results import sha256_bytes, sha256_json

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = {'clean', 'missing_paragraph', 'noise', 'duplicate', 'reorder', 'instruction_interference'}


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


class FreezeV7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.freeze = load('outputs/p3.freeze.v7.json')
        cls.manifest = load('samples/p3_manifest.json')

    def test_version_and_counts(self):
        self.assertEqual(self.freeze['freeze_version'], 7)
        self.assertEqual(len(self.freeze['cases']), 12)
        self.assertEqual(self.freeze['counts']['splits'], {'frozen_test': 12})

    def test_no_truncation(self):
        self.assertTrue(all(c['source_truncated'] is False for c in self.freeze['cases']))

    def test_two_templates_six_variants(self):
        by_template = {}
        for c in self.freeze['cases']:
            by_template.setdefault(c['template'], set()).add(c['case_id'].rsplit('-', 1)[1])
        self.assertEqual(set(by_template), {'p3_npr_text', 'p3_gnu_essay'})
        for variants in by_template.values():
            self.assertEqual(variants, VARIANTS)

    def test_batch_config_frozen(self):
        self.assertEqual(self.freeze['batch_config'],
                         {'max_source_chars': 20000, 'max_output_tokens': 2200,
                          'timeout_seconds': 90, 'model': 'qwen3.8-27b'})

    def test_manifest_matches_freeze(self):
        mids = {c['case_id'] for c in self.manifest['cases']}
        fids = {c['case_id'] for c in self.freeze['cases']}
        self.assertEqual(mids, fids)
        self.assertEqual(sha256_json(self.manifest), self.freeze['manifest_sha256'])

    def test_file_hashes(self):
        # v3 was built under judge v1.3 (later rolled back after dev GUARD_FAIL).
        # Freeze v7 is the historical record of that build: its judge sha must
        # equal the failed v1.3 sha (freeze v6), while all other files match disk.
        v6 = load('outputs/rubrics_judge.node3.freeze.v6.json')
        for rel, sha in self.freeze['files'].items():
            if rel == 'src/webextractor/rubrics_judge.py':
                self.assertEqual(sha, v6['files'][rel])
            else:
                self.assertEqual(sha256_bytes((ROOT / rel).read_bytes()), sha, rel)

    def test_case_hashes(self):
        for c in self.freeze['cases']:
            cid = c['case_id']
            cand = load('samples/calibration/' + cid + '.candidate.json')
            lab = load('samples/calibration/labels/' + cid + '.label.json')
            self.assertEqual(sha256_json(cand), c['candidate_sha256'])
            self.assertEqual(sha256_json(lab), c['label_sha256'])
            self.assertEqual(lab['label_origin'], 'assistant_silver')
            self.assertFalse(lab['human_reviewed'])

    def test_isolation_from_prior_manifests(self):
        prior = set()
        for rel in ('samples/calibration_manifest.json', 'samples/p2_manifest.json'):
            prior |= {c['case_id'] for c in load(rel)['cases']}
        current = {c['case_id'] for c in self.manifest['cases']}
        self.assertFalse(prior & current)

    def test_source_provenance(self):
        for name in ('p3_npr_text', 'p3_gnu_essay'):
            prov = load('samples/' + name + '.html.source.json')
            raw = (ROOT / 'samples' / (name + '.html')).read_bytes()
            self.assertEqual(sha256_bytes(raw), prov['sha256'])
            self.assertLessEqual(prov['raw_chars'], 20000)
            self.assertGreaterEqual(prov['raw_chars'], 5000)
            self.assertTrue(prov['fetch_log'])

    def test_blind_kit_exists(self):
        kit = ROOT / 'outputs/human_review/p3.blind.v1'
        self.assertTrue((kit / 'human_labels.blind.json').exists())
        self.assertTrue((kit / 'INDEX.md').exists() or (kit / 'index.md').exists()
                        or any(kit.glob('*.md')))


if __name__ == '__main__':
    unittest.main()
