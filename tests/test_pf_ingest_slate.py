# -*- coding: utf-8 -*-
"""Tests for the opt-in --slate integrity chain (P-F v4 kit layout).

Default (no slate) behavior must stay byte-identical; slate mode verifies
kit inputs.slate -> formal slate -> manifest file sha / freeze file sha.
Uses only immutable committed artifacts (never the mutable filled labels).
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools import ingest_p2_human_labels as ing

ROOT = Path(__file__).resolve().parents[1]
MP = ROOT / 'samples/pf_v4_manifest.json'
FP = ROOT / 'outputs/pf.freeze.v1.json'
KD = ROOT / 'outputs/human_review/pf.v4.blind.v1'
SP = ROOT / 'outputs/pf.v4.slate.v2/pf_v4_slate.formal.json'


def _load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


class PfSlateIntegrityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_slate_chain_passes(self):
        problems, _ = ing.verify_integrity(MP, FP, KD, _load(MP), _load(FP), slate_path=SP)
        self.assertEqual(problems, [])

    def test_default_mode_unchanged_on_pf_kit(self):
        # Without --slate the v2/v3 inputs.manifest/freeze checks still run,
        # and the pf kit (slate-only inputs) must fail them exactly as before.
        problems, _ = ing.verify_integrity(MP, FP, KD, _load(MP), _load(FP))
        self.assertTrue(any('kit manifest input sha' in p for p in problems))
        # Note: pf freeze has no amendment, so base_sha=None coincidentally
        # equals the missing inputs.freeze=None (pre-existing behavior); the
        # manifest check alone already rejects the slate-only kit layout.

    def test_slate_file_drift_rejected(self):
        bad = self.tmp / 'slate.json'
        bad.write_bytes(SP.read_bytes() + b' ')
        problems, _ = ing.verify_integrity(MP, FP, KD, _load(MP), _load(FP), slate_path=bad)
        self.assertTrue(any('kit slate input sha' in p for p in problems))

    def test_slate_manifest_sha_drift_rejected(self):
        slate = _load(SP)
        slate['manifest_sha256'] = 'deadbeef'
        bad = self.tmp / 'slate.json'
        bad.write_text(json.dumps(slate), encoding='utf-8')
        problems, _ = ing.verify_integrity(MP, FP, KD, _load(MP), _load(FP), slate_path=bad)
        self.assertTrue(any('slate manifest sha' in p for p in problems))

    def test_slate_freeze_sha_drift_rejected(self):
        slate = _load(SP)
        slate['freeze_sha256'] = 'deadbeef'
        bad = self.tmp / 'slate.json'
        bad.write_text(json.dumps(slate), encoding='utf-8')
        problems, _ = ing.verify_integrity(MP, FP, KD, _load(MP), _load(FP), slate_path=bad)
        self.assertTrue(any('slate freeze sha' in p for p in problems))

    def test_kit_slate_input_drift_rejected(self):
        kd = self.tmp / 'kit'
        shutil.copytree(KD, kd)
        km = _load(kd / 'kit_manifest.json')
        km['inputs']['slate'] = 'deadbeef'
        (kd / 'kit_manifest.json').write_text(json.dumps(km), encoding='utf-8')
        problems, _ = ing.verify_integrity(MP, FP, kd, _load(MP), _load(FP), slate_path=SP)
        self.assertTrue(any('kit slate input sha' in p for p in problems))

    def test_freeze_data_drift_still_checked_in_slate_mode(self):
        freeze = _load(FP)
        rel = 'samples/pf_v4_debian.html'
        freeze['files'][rel] = 'deadbeef'
        problems, _ = ing.verify_integrity(MP, FP, KD, _load(MP), freeze, slate_path=SP)
        self.assertIn('freeze file drift: ' + rel, problems)


if __name__ == '__main__':
    unittest.main()
