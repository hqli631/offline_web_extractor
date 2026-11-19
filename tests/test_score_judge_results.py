# -*- coding: utf-8 -*-
import unittest

from tools.score_judge_results import (DIMS, aggregate, check_freeze, compare_case,
                                       stability_compare)


def label(mutation='clean', severe=False, decision='pass'):
    dims = {n: {'score': 4, 'status': 'scored', 'severity': 'none'} for n in DIMS}
    dims['format'] = {'score': None, 'status': 'not_applicable', 'severity': 'none'}
    if severe:
        dims['cleanliness'] = {'score': 2, 'status': 'scored', 'severity': 'major'}
    return {'mutation': {'type': mutation}, 'source_truncated': False,
            'expected': {'dimensions': dims, 'decision': decision, 'needs_human_review': severe}}


def judge_dims(severity='none', score=4):
    dims = {n: {'score': score, 'status': 'scored', 'severity': severity} for n in DIMS}
    dims['format'] = {'score': None, 'status': 'not_applicable', 'severity': 'none'}
    if severity in ('major', 'critical'):
        dims['cleanliness'] = {'score': 2, 'status': 'scored', 'severity': severity}
    return dims


def case_row(cid='c1', status='accepted', severity='none', score=4, decision='pass',
             review=False, mutation='clean', split='development'):
    report = {'status': status, 'elapsed_seconds': 1.0,
              'usage': {'input_tokens': 10, 'output_tokens': 5, 'total_tokens': 15}}
    if status == 'accepted':
        report['assessment'] = {'dimensions': judge_dims(severity, score), 'decision': decision,
                                'needs_human_review': review}
        report['program_assessment'] = {'dimensions': judge_dims()}
    else:
        report['error'] = {'type': 'ValueError', 'stage': 'validation', 'detail': 'x'}
    return {'case_id': cid, 'split': split, 'template': 't', 'cache_hit': False,
            'case_meta': {'candidate_sha256': 'a', 'source_sha256': 'b', 'gold_sha256': 'c'},
            'report': report}


def freeze_for(rows):
    return {'manifest_sha256': 'm', 'files': {'samples/calibration_manifest.json': 'm'}, 'batch_config': {'model': 'qwen3.8-27b', 'max_source_chars': 20000,
                                                     'max_output_tokens': 2200, 'timeout_seconds': 90},
            'cases': [{'case_id': r['case_id'], **r['case_meta']} for r in rows]}


def batch_for(rows):
    return {'manifest_sha256': 'm', 'signature': {'model': 'qwen3.8-27b', 'max_source_chars': 20000,
                                                  'max_output_tokens': 2200, 'timeout_seconds': 90},
            'cases': rows}


class MetricsTests(unittest.TestCase):
    def test_perfect_agreement(self):
        row, reasons = compare_case(case_row(), label())
        self.assertTrue(row['decision_match'])
        self.assertTrue(all(row['dimensions'][n]['exact'] for n in DIMS))
        self.assertEqual(reasons, [])
        agg = aggregate([row])
        self.assertEqual(agg['dim_exact_rate'], 1.0)
        self.assertEqual(agg['decision_match_rate'], 1.0)
        self.assertEqual(agg['failure_rate'], 0.0)

    def test_severe_miss_and_false_alarm(self):
        row, reasons = compare_case(case_row(decision='pass'), label(severe=True, decision='fail'))
        self.assertTrue(row['severe_miss'])
        self.assertFalse(row['false_alarm'])
        self.assertIn('severe_miss', reasons)
        row2, reasons2 = compare_case(case_row(severity='major', decision='fail'), label())
        self.assertTrue(row2['false_alarm'])
        self.assertFalse(row2['severe_miss'])
        self.assertIn('false_alarm', reasons2)

    def test_within1_and_error_handling(self):
        row, _ = compare_case(case_row(score=3, decision='uncertain', review=True), label())
        self.assertFalse(row['dimensions']['completeness']['exact'])
        self.assertTrue(row['dimensions']['completeness']['within1'])
        err, reasons = compare_case(case_row(status='error'), label())
        self.assertIn('judge_error', reasons)
        agg = aggregate([row, err])
        self.assertEqual(agg['accepted'], 1)
        self.assertEqual(agg['failure_rate'], 0.5)

    def test_injection_compliance_detected(self):
        row, reasons = compare_case(case_row(mutation='instruction_interference'),
                                    label(mutation='instruction_interference', severe=True, decision='fail'))
        self.assertTrue(row['injection_complied'])
        self.assertIn('injection_complied', reasons)
        self.assertIn('injection_not_flagged_severe', reasons)
        row2, reasons2 = compare_case(case_row(severity='major', decision='fail', mutation='instruction_interference'),
                                      label(mutation='instruction_interference', severe=True, decision='fail'))
        self.assertFalse(row2['injection_complied'])
        self.assertNotIn('injection_complied', reasons2)

    def test_stability_identity_and_diff(self):
        base, _ = compare_case(case_row(), label())
        stab = {'cases': [case_row(cid='c1'), case_row(cid='c2', score=3, decision='uncertain')]}
        base2, _ = compare_case(case_row(cid='c2'), label())
        result = stability_compare([base, base2], stab)
        self.assertEqual(result['n_cases'], 2)
        self.assertEqual(result['identical'], 1)
        self.assertEqual(result['cases'][1]['diffs'],
                         [n + ':score' for n in DIMS if n != 'format'] + ['decision'])

    def test_freeze_integrity_fail_closed(self):
        rows = [case_row()]
        self.assertEqual(check_freeze(batch_for(rows), {'cases': []}, freeze_for(rows)), [])
        bad = freeze_for(rows)
        bad['cases'][0]['candidate_sha256'] = 'drifted'
        self.assertTrue(any('candidate_sha256 drift' in p for p in check_freeze(batch_for(rows), {'cases': []}, bad)))
        bad_cfg = freeze_for(rows)
        bad_cfg['batch_config']['max_source_chars'] = 40000
        self.assertTrue(any('max_source_chars' in p for p in check_freeze(batch_for(rows), {'cases': []}, bad_cfg)))
        bad_manifest = batch_for(rows)
        bad_manifest['manifest_sha256'] = 'other'
        self.assertTrue(any('manifest' in p for p in check_freeze(bad_manifest, {'cases': []}, freeze_for(rows))))
        no_files = freeze_for(rows)
        del no_files['files']
        self.assertTrue(any('manifest' in p for p in check_freeze(batch_for(rows), {'cases': []}, no_files)))

    def test_freeze_manifest_file_and_canonical_hashes(self):
        import json as _json
        import tempfile
        from pathlib import Path as _Path
        from tools.score_judge_results import sha256_bytes, sha256_json
        rows = [case_row()]
        manifest_obj = {'judge_manifest_version': 1, 'cases': [{'case_id': 'c1'}]}
        with tempfile.TemporaryDirectory() as tmp:
            mp = _Path(tmp) / 'calibration_manifest.json'
            mp.write_text(_json.dumps(manifest_obj, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            freeze = freeze_for(rows)
            freeze['files']['samples/calibration_manifest.json'] = sha256_bytes(mp.read_bytes())
            freeze['manifest_sha256'] = sha256_json(manifest_obj)
            batch = batch_for(rows)
            batch['manifest_sha256'] = sha256_bytes(mp.read_bytes())
            self.assertEqual(check_freeze(batch, {'cases': []}, freeze, mp), [])
            mp.write_text(_json.dumps(manifest_obj) + '\n\n', encoding='utf-8')
            self.assertTrue(check_freeze(batch, {'cases': []}, freeze, mp))


if __name__ == '__main__':
    unittest.main()
