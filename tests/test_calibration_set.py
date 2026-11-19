# -*- coding: utf-8 -*-
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from tools.build_calibration_set import (BASES, INJECTION, LABEL_ORIGIN, NOISE_TERMS,
                                         _freeze_entries, build_all, check_manifest_isolation,
                                         derive_expected, dump, mutate, sha256_bytes)
from tools.run_rubrics_judge import load_manifest

ROOT = Path(__file__).resolve().parents[1]

DOC = {'title': '1. Test Title', 'blocks': [
    {'kind': 'heading', 'text': 'Test Title', 'heading_level': 1, 'list_type': None, 'depth': 0, 'ordinal': None},
    {'kind': 'paragraph', 'text': 'First paragraph with enough length to qualify as meaningful content.', 'list_type': None, 'depth': 0, 'ordinal': None},
    {'kind': 'paragraph', 'text': 'Second paragraph also long enough to qualify as meaningful content here.', 'list_type': None, 'depth': 0, 'ordinal': None},
    {'kind': 'code', 'text': 'def f():\n    return 1\n', 'list_type': None, 'depth': 0, 'ordinal': None},
]}


class CalibrationTests(unittest.TestCase):
    def test_clean_is_identity_and_deterministic(self):
        a, meta_a = mutate(DOC, 'clean', 'en')
        b, meta_b = mutate(DOC, 'clean', 'en')
        self.assertEqual(a, DOC)
        self.assertEqual(a, b)
        self.assertEqual(meta_a, meta_b)
        self.assertEqual(meta_a['type'], 'clean')

    def test_missing_paragraph_removes_first_long_paragraph(self):
        out, meta = mutate(DOC, 'missing_paragraph', 'en')
        self.assertEqual(meta['index'], 1)
        self.assertEqual(len(out['blocks']), len(DOC['blocks']) - 1)
        self.assertEqual(out['blocks'][1]['text'], DOC['blocks'][2]['text'])
        self.assertEqual(DOC['blocks'][1]['text'], 'First paragraph with enough length to qualify as meaningful content.')

    def test_noise_and_injection_insert_untrusted_block(self):
        out, meta = mutate(DOC, 'noise', 'zh')
        self.assertEqual(meta['index'], 1)
        self.assertIn('分享到', out['blocks'][1]['text'])
        out2, meta2 = mutate(DOC, 'instruction_interference', 'en')
        self.assertEqual(out2['blocks'][1]['text'], INJECTION)
        self.assertTrue(meta2['must_not_comply'])
        self.assertEqual(len(out2['blocks']), len(DOC['blocks']) + 1)

    def test_duplicate_and_reorder(self):
        out, meta = mutate(DOC, 'duplicate', 'en')
        self.assertEqual(out['blocks'][2], out['blocks'][1])
        self.assertEqual(len(out['blocks']), len(DOC['blocks']) + 1)
        out2, meta2 = mutate(DOC, 'reorder', 'en')
        self.assertEqual(meta2['indices'], [1, 2])
        self.assertEqual(out2['blocks'][1]['text'], DOC['blocks'][2]['text'])
        self.assertEqual(out2['blocks'][2]['text'], DOC['blocks'][1]['text'])
        self.assertEqual(len(out2['blocks']), len(DOC['blocks']))

    def test_title_number_strips_prefix(self):
        out, meta = mutate(DOC, 'title_number', 'zh')
        self.assertEqual(out['title'], 'Test Title')
        self.assertEqual(meta['before'], '1. Test Title')
        with self.assertRaises(ValueError):
            mutate({'title': 'No Number', 'blocks': []}, 'title_number', 'en')

    def test_code_indent_changes_whitespace_only(self):
        out, meta = mutate(DOC, 'code_indent', 'en')
        before = DOC['blocks'][3]['text']
        after = out['blocks'][3]['text']
        self.assertNotEqual(before, after)
        self.assertEqual(before.replace(' ', ''), after.replace(' ', ''))
        self.assertEqual(meta['block'], 3)
        self.assertEqual(out['blocks'][3]['kind'], 'code')

    def test_silver_with_gold_clean_pass_and_defect_fail(self):
        expected, decision, review, derivation, prog = derive_expected(DOC, DOC, [], False)
        self.assertEqual(decision, 'pass')
        self.assertFalse(review)
        self.assertEqual(derivation, 'frozen_rubrics_v2_program_on_controlled_mutation')
        self.assertIsNotNone(prog)
        missing, _ = mutate(DOC, 'missing_paragraph', 'en')
        expected2, decision2, _, _, _ = derive_expected(missing, DOC, [], False)
        self.assertLess(expected2['completeness']['score'], 4)
        self.assertEqual(decision2, 'fail')
        noisy, _ = mutate(DOC, 'noise', 'zh')
        expected3, decision3, _, _, _ = derive_expected(noisy, DOC, NOISE_TERMS['zh'], False)
        self.assertEqual(expected3['cleanliness']['severity'], 'major')
        self.assertEqual(decision3, 'fail')

    def test_silver_source_only_provisional_and_defect(self):
        expected, decision, review, derivation, prog = derive_expected(DOC, None, [], False)
        self.assertEqual(decision, 'uncertain')
        self.assertTrue(review)
        self.assertIsNone(prog)
        self.assertEqual(derivation, 'assistant_expectation_no_gold')
        self.assertEqual(expected['format']['score'], 4)
        expected2, decision2, _, _, _ = derive_expected(DOC, None, [], False, source_only_defect=True)
        self.assertEqual(expected2['cleanliness']['severity'], 'major')
        self.assertEqual(decision2, 'fail')
        no_code = {'title': 'T', 'blocks': [{'kind': 'paragraph', 'text': 'x'}]}
        expected3, _, _, _, _ = derive_expected(no_code, None, [], False)
        self.assertEqual(expected3['format']['status'], 'not_applicable')

    def test_split_isolation_rejects_leakage(self):
        cases = [{'source': 'a.html', 'split': 'development'}, {'source': 'b.html', 'split': 'frozen_test'}]
        self.assertTrue(check_manifest_isolation(cases))
        cases.append({'source': 'a.html', 'split': 'frozen_test'})
        with self.assertRaises(ValueError):
            check_manifest_isolation(cases)

    def test_freeze_file_entries_hash_serialized_bytes(self):
        built = build_all(ROOT / 'samples')
        manifest = {'judge_manifest_version': 1, 'cases': [i['manifest_case'] for i in built]}
        manifest_bytes = dump(manifest).encode('utf-8')
        entries = _freeze_entries(built, ROOT / 'samples', manifest_bytes)
        for item in built:
            cid = item['case_id']
            self.assertEqual(entries['samples/calibration/' + cid + '.candidate.json'],
                             sha256_bytes(dump(item['candidate']).encode('utf-8')))
            self.assertEqual(entries['samples/calibration/labels/' + cid + '.label.json'],
                             sha256_bytes(dump(item['label']).encode('utf-8')))
        self.assertEqual(entries['samples/calibration_manifest.json'], sha256_bytes(manifest_bytes))
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / 'probe.json'
            probe.write_text(dump(built[0]['candidate']), encoding='utf-8', newline='')
            self.assertEqual(sha256_bytes(probe.read_bytes()),
                             entries['samples/calibration/' + built[0]['case_id'] + '.candidate.json'])

    def test_build_all_schema_counts_and_manifest_valid(self):
        built = build_all(ROOT / 'samples')
        self.assertEqual(len(built), 23)
        counts = {}
        for item in built:
            split = item['manifest_case']['split']
            counts[split] = counts.get(split, 0) + 1
            label = item['label']
            self.assertEqual(label['label_origin'], LABEL_ORIGIN)
            self.assertFalse(label['human_reviewed'])
            self.assertIn('title', item['candidate'])
            self.assertIsInstance(item['candidate']['blocks'], list)
            self.assertEqual(set(label['expected']['dimensions']),
                             {'completeness', 'cleanliness', 'structure', 'title', 'format'})
            self.assertIn(label['expected']['decision'], ('pass', 'uncertain', 'fail'))
        self.assertEqual(counts, {'development': 12, 'frozen_test': 11})
        self.assertFalse(any('rfc' in item['case_id'] for item in built))
        manifest = {'judge_manifest_version': 1, 'cases': [item['manifest_case'] for item in built]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'manifest.json'
            path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
            loaded = load_manifest(path)
        self.assertEqual(len(loaded['cases']), 23)
        again = build_all(ROOT / 'samples')
        self.assertEqual([i['candidate'] for i in built], [i['candidate'] for i in again])
        self.assertEqual([i['label'] for i in built], [i['label'] for i in again])


if __name__ == '__main__':
    unittest.main()
