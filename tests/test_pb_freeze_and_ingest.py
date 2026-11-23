# -*- coding: utf-8 -*-
"""Tests for P-B freeze amendment v9 and ingest tool generalization."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import amend_freeze_v9 as az
from tools import ingest_p2_human_labels as ing

ROOT = Path(__file__).resolve().parents[1]


def _load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


class AmendFreezeV9Test(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.out = self.tmp / 'v9.json'

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_happy_path_only_judge_pin_changes(self):
        res = az.build(ROOT / az.PARENT, self.out)
        v7 = _load(ROOT / az.PARENT)
        v9 = _load(self.out)
        self.assertEqual(v9['files'][az.JUDGE_REL], az.V12_SHA)
        for rel, h in v7['files'].items():
            if rel != az.JUDGE_REL:
                self.assertEqual(v9['files'][rel], h)
        self.assertEqual(v9['cases'], v7['cases'])
        self.assertEqual(v9['manifest_sha256'], v7['manifest_sha256'])
        self.assertEqual(v9['batch_config'], v7['batch_config'])
        self.assertEqual(v9['amendment']['base_freeze_sha256'], az.PARENT_SHA)
        self.assertTrue(v9['amendment']['data_unchanged'])
        self.assertEqual(res['data_files_verified'], len(v7['files']) - 1)

    def test_dry_run_writes_nothing(self):
        res = az.build(ROOT / az.PARENT, self.out, dry_run=True)
        self.assertTrue(res['dry_run'])
        self.assertFalse(self.out.exists())

    def test_overwrite_refusal(self):
        az.build(ROOT / az.PARENT, self.out)
        with self.assertRaises(FileExistsError):
            az.build(ROOT / az.PARENT, self.out)

    def test_judge_not_restored_fails(self):
        with mock.patch.object(az, 'V12_SHA', 'deadbeef'):
            with self.assertRaises(ValueError):
                az.build(ROOT / az.PARENT, self.out)

    def test_parent_sha_drift_fails(self):
        bad = self.tmp / 'bad_parent.json'
        bad.write_bytes((ROOT / az.PARENT).read_bytes() + b' ')
        with self.assertRaises(ValueError):
            az.build(bad, self.out)

    def test_data_drift_fails(self):
        v7 = _load(ROOT / az.PARENT)
        root = self.tmp / 'root'
        for rel in v7['files']:
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, dst)
        victim = root / 'samples/p3_npr_text.html'
        victim.write_bytes(victim.read_bytes() + b' ')
        with self.assertRaises(ValueError):
            az.build(ROOT / az.PARENT, self.out, root=root)


class IngestGeneralizationTest(unittest.TestCase):
    def test_p2_integrity_preserved(self):
        mp = ROOT / 'samples/p2_manifest.json'
        fp = ROOT / 'outputs/p2.freeze.v5.json'
        kd = ROOT / 'outputs/human_review/p2.blind.v1'
        problems, _ = ing.verify_integrity(mp, fp, kd, _load(mp), _load(fp))
        self.assertEqual(problems, [])

    def test_v3_amendment_integrity_passes(self):
        mp = ROOT / 'samples/p3_manifest.json'
        fp = ROOT / 'outputs/pb.freeze.v9.json'
        kd = ROOT / 'outputs/human_review/p3.blind.v1'
        problems, _ = ing.verify_integrity(mp, fp, kd, _load(mp), _load(fp))
        self.assertEqual(problems, [])

    def test_v3_original_freeze_still_flags_judge_drift(self):
        mp = ROOT / 'samples/p3_manifest.json'
        fp = ROOT / 'outputs/p3.freeze.v7.json'
        kd = ROOT / 'outputs/human_review/p3.blind.v1'
        problems, _ = ing.verify_integrity(mp, fp, kd, _load(mp), _load(fp))
        self.assertIn('freeze file drift: ' + az.JUDGE_REL, problems)

    def test_unrelated_amendment_base_rejected(self):
        mp = ROOT / 'samples/p3_manifest.json'
        fp = ROOT / 'outputs/pb.freeze.v9.json'
        kd = ROOT / 'outputs/human_review/p3.blind.v1'
        freeze = _load(fp)
        freeze['amendment']['base_freeze_sha256'] = 'unrelated'
        problems, _ = ing.verify_integrity(mp, fp, kd, _load(mp), freeze)
        self.assertTrue(any('kit freeze input sha' in p for p in problems))

    def test_manifest_rel_lookup_generalized(self):
        mp = ROOT / 'samples/p3_manifest.json'
        fp = ROOT / 'outputs/pb.freeze.v9.json'
        kd = ROOT / 'outputs/human_review/p3.blind.v1'
        freeze = _load(fp)
        del freeze['files']['samples/p3_manifest.json']
        problems, _ = ing.verify_integrity(mp, fp, kd, _load(mp), freeze)
        self.assertTrue(any('manifest file sha256' in p for p in problems))


if __name__ == '__main__':
    unittest.main()
