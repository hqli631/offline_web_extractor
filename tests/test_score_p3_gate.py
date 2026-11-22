# -*- coding: utf-8 -*-
"""Unit tests for tools/score_p3_gate.py (offline, zero model calls)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.score_p3_gate import (m_pass_recall, severe_miss_count,
                                 validate_gate_config, check_data_freeze,
                                 check_protocol, evaluate_gate, main)
from tools.score_judge_results import sha256_bytes, sha256_json, DIMS

DIMS5 = DIMS


def cfg(**over):
    base = {'status': 'frozen', 'approved_by': 'tester', 'approved_at': '2026-11-22',
            'seed': 7, 'B': 200,
            'batch_config': {'model': 'test-model', 'judge_version': '1.3.0',
                             'rubrics_version': '2.0.0', 'max_source_chars': 20000,
                             'max_output_tokens': 4096, 'timeout_seconds': 120},
            'dev': {'reject_rate_lt': 0.10, 'severe_miss_count_le': 1,
                    'false_alarm_rate_le': 0.15, 'decision_match_ge': 0.85,
                    'kappa_ge': 0.75, 'match_kappa_subset_label': 'orig'},
            'v3': {'reject_rate_lt': 0.10, 'severe_miss_count_le': 1,
                   'false_alarm_rate_le': 0.15, 'decision_match_ge': 0.80,
                   'pass_recall_ge': 0.80}}
    base.update(over)
    return base


def rec(cid, human='uncertain', judge='uncertain', status='accepted',
        severe_miss=False, false_alarm=False):
    return {'case_id': cid, 'split': 'development', 'judge_status': status,
            'human_decision': human, 'judge_decision': judge,
            'decision_match': status == 'accepted' and human == judge,
            'severe_miss': severe_miss, 'false_alarm': false_alarm,
            'dimensions': {n: {'comparable': True, 'exact': True, 'within1': True,
                               'severity_sign_match': True,
                               'human_status': 'scored', 'judge_status': 'scored'}
                           for n in DIMS5}}


def dev_pool():
    orig = ([rec('o%d' % i, 'pass', 'pass') for i in range(6)]
            + [rec('f%d' % i, 'fail', 'fail') for i in range(6)])
    p2dev = [rec('p%d' % i) for i in range(6)]
    return {'orig': orig, 'p2dev': p2dev}


def v3_pool(n_pass=6):
    return ([rec('v%d' % i, 'pass', 'pass') for i in range(n_pass)]
            + [rec('u%d' % i) for i in range(6)])


class MetricTests(unittest.TestCase):
    def test_pass_recall_basic(self):
        recs = [rec('a', 'pass', 'pass'), rec('b', 'pass', 'uncertain'),
                rec('c', 'pass', 'pass'), rec('d', 'uncertain', 'pass')]
        self.assertAlmostEqual(m_pass_recall(recs), 2 / 3)

    def test_pass_recall_no_human_pass(self):
        self.assertIsNone(m_pass_recall([rec('a'), rec('b', 'fail', 'fail')]))

    def test_pass_recall_excludes_rejected(self):
        recs = [rec('a', 'pass', 'pass'), rec('b', 'pass', 'pass', status='error')]
        self.assertEqual(m_pass_recall(recs), 1.0)
        self.assertIsNone(m_pass_recall([rec('b', 'pass', 'pass', status='error')]))

    def test_severe_miss_count(self):
        recs = [rec('a', severe_miss=True), rec('b', severe_miss=True, status='error'),
                rec('c')]
        self.assertEqual(severe_miss_count(recs), 1)


class ConfigTests(unittest.TestCase):
    def test_valid_frozen_config(self):
        self.assertEqual(validate_gate_config(cfg()), [])

    def test_draft_refused(self):
        problems = validate_gate_config(cfg(status='draft'))
        self.assertTrue(any('frozen' in p for p in problems))

    def test_missing_approval(self):
        c = cfg()
        del c['approved_by']
        self.assertTrue(any('approved_by' in p for p in validate_gate_config(c)))

    def test_missing_threshold(self):
        c = cfg()
        del c['v3']['pass_recall_ge']
        self.assertTrue(any('pass_recall_ge' in p for p in validate_gate_config(c)))

    def test_missing_judge_version_pin(self):
        c = cfg()
        del c['batch_config']['judge_version']
        self.assertTrue(any('judge_version' in p for p in validate_gate_config(c)))

    def test_out_of_range_threshold(self):
        c = cfg()
        c['dev']['false_alarm_rate_le'] = 1.5
        self.assertTrue(any('out of [0,1]' in p for p in validate_gate_config(c)))


class IntegrityTests(unittest.TestCase):
    def test_protocol_mismatch(self):
        batch = {'signature': dict(cfg()['batch_config'], judge_version='1.2.0')}
        problems = check_protocol(batch, cfg())
        self.assertTrue(any('judge_version' in p for p in problems))

    def test_protocol_ok(self):
        self.assertEqual(check_protocol({'signature': cfg()['batch_config']}, cfg()), [])

    def test_data_freeze_drift(self):
        batch = {'manifest_sha256': 'h1',
                 'cases': [{'case_id': 'c1', 'case_meta': {'candidate_sha256': 'X'}}]}
        freeze = {'files': {'samples/m.json': 'h1'},
                  'cases': [{'case_id': 'c1', 'candidate_sha256': 'Y'}]}
        problems = check_data_freeze(batch, freeze)
        self.assertTrue(any('candidate_sha256 drift' in p for p in problems))

    def test_data_freeze_manifest_not_frozen(self):
        batch = {'manifest_sha256': 'other', 'cases': []}
        freeze = {'files': {'samples/m.json': 'h1'}, 'cases': []}
        self.assertTrue(check_data_freeze(batch, freeze))

    def test_data_freeze_ok(self):
        batch = {'manifest_sha256': 'h1',
                 'cases': [{'case_id': 'c1', 'case_meta': {'candidate_sha256': 'Y'}}]}
        freeze = {'files': {'samples/m.json': 'h1'},
                  'cases': [{'case_id': 'c1', 'candidate_sha256': 'Y'}]}
        self.assertEqual(check_data_freeze(batch, freeze), [])


class GateTests(unittest.TestCase):
    def test_pass_clean(self):
        gate = evaluate_gate(dev_pool(), v3_pool(), cfg())
        self.assertEqual(gate['verdict'], 'PASS')
        self.assertTrue(all(c['pass'] for c in gate['checks']))

    def test_fail_false_alarm(self):
        dev = dev_pool()
        for r in dev['p2dev'][:3]:
            r['false_alarm'] = True
        gate = evaluate_gate(dev, v3_pool(), cfg())
        self.assertEqual(gate['verdict'], 'FAIL')
        c = [c for c in gate['checks'] if c['metric'] == 'false_alarm_rate'
             and c['scope'] == 'dev_pooled'][0]
        self.assertFalse(c['pass'])

    def test_fail_severe_miss_count(self):
        dev = dev_pool()
        dev['orig'][0]['severe_miss'] = True
        dev['p2dev'][0]['severe_miss'] = True
        gate = evaluate_gate(dev, v3_pool(), cfg())
        self.assertEqual(gate['verdict'], 'FAIL')

    def test_fail_reject_rate(self):
        dev = dev_pool()
        for r in dev['p2dev'][:2]:
            r['judge_status'] = 'error'
        gate = evaluate_gate(dev, v3_pool(), cfg())
        self.assertEqual(gate['verdict'], 'FAIL')
        c = [c for c in gate['checks'] if c['metric'] == 'reject_rate'
             and c['scope'] == 'dev_pooled'][0]
        self.assertFalse(c['pass'])

    def test_fail_v3_pass_recall(self):
        v3 = v3_pool(n_pass=5)
        for r in v3[:2]:
            r['judge_decision'] = 'uncertain'
            r['decision_match'] = False
        gate = evaluate_gate(dev_pool(), v3, cfg())
        self.assertEqual(gate['verdict'], 'FAIL')
        c = [c for c in gate['checks'] if c['metric'] == 'pass_recall'][0]
        self.assertFalse(c['pass'])
        self.assertEqual(c['observed'], 0.6)

    def test_fail_v3_no_human_pass(self):
        v3 = [rec('u%d' % i) for i in range(12)]
        gate = evaluate_gate(dev_pool(), v3, cfg())
        self.assertEqual(gate['verdict'], 'FAIL')
        c = [c for c in gate['checks'] if c['metric'] == 'pass_recall'][0]
        self.assertIsNone(c['observed'])
        self.assertIn('untestable', c['note'])

    def test_fail_kappa_subset(self):
        dev = dev_pool()
        for r in dev['orig'][:3]:
            r['judge_decision'] = 'fail'
            r['decision_match'] = False
        for r in dev['orig'][6:9]:
            r['judge_decision'] = 'pass'
            r['decision_match'] = False
        gate = evaluate_gate(dev, v3_pool(), cfg())
        self.assertEqual(gate['verdict'], 'FAIL')
        c = [c for c in gate['checks'] if c['metric'] == 'cohen_kappa'][0]
        self.assertFalse(c['pass'])

    def test_fail_kappa_degenerate_subset(self):
        dev = dev_pool()
        dev['orig'] = [rec('o%d' % i) for i in range(12)]
        gate = evaluate_gate(dev, v3_pool(), cfg())
        self.assertEqual(gate['verdict'], 'FAIL')
        c = [c for c in gate['checks'] if c['metric'] == 'cohen_kappa'][0]
        self.assertIn('degenerate', c['note'])

    def test_kappa_threshold_only_on_subset(self):
        dev = dev_pool()  # p2dev all uncertain; pooled kappa would degenerate
        gate = evaluate_gate(dev, v3_pool(), cfg())
        self.assertEqual(gate['verdict'], 'PASS')
        self.assertEqual(gate['kappa_subset_label'], 'orig')


def _dims(score=4, severity='none'):
    return {n: {'score': score, 'status': 'scored', 'severity': severity} for n in DIMS5}


def _case(cid, split, decision, hashes):
    return {'case_id': cid, 'split': split, 'case_meta': dict(hashes),
            'report': {'status': 'accepted',
                       'assessment': {'decision': decision, 'dimensions': _dims()}}}


def _gold(cid, decision):
    return {'case_id': cid, 'decision': decision, 'dimensions': _dims()}


class MainTests(unittest.TestCase):
    def _write(self, d, name, value):
        p = Path(d) / name
        p.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8', newline='')
        return p

    def _fixture(self, d, v3_judge_first='pass'):
        manifest = {'cases': []}
        mp = self._write(d, 'manifest.json', manifest)
        msha = sha256_bytes(mp.read_bytes())
        sig = cfg()['batch_config']

        def batch_freeze(name, cases, golds):
            hashes = {c['case_id']: {'candidate_sha256': 'cand-' + c['case_id'],
                                     'source_sha256': 'src-' + c['case_id'],
                                     'gold_sha256': 'gold-' + c['case_id']}
                      for c in cases}
            rows = [_case(g['case_id'], g['split'],
                          g['judge'], hashes[g['case_id']]) for g in golds]
            batch = {'manifest_sha256': msha, 'signature': sig, 'cases': rows}
            freeze = {'files': {'manifest.json': msha}, 'manifest_sha256': sha256_json(manifest),
                      'cases': [dict(case_id=cid, **h) for cid, h in hashes.items()]}
            bp = self._write(d, name + '.batch.json', batch)
            fp = self._write(d, name + '.freeze.json', freeze)
            gp = self._write(d, name + '.gold.json',
                             {'cases': [_gold(g['case_id'], g['human']) for g in golds]})
            return bp, fp, gp

        orig = ([{'case_id': 'o%d' % i, 'split': 'development', 'human': 'pass', 'judge': 'pass'}
                 for i in range(6)]
                + [{'case_id': 'f%d' % i, 'split': 'development', 'human': 'fail', 'judge': 'fail'}
                   for i in range(6)])
        p2dev = [{'case_id': 'p%d' % i, 'split': 'development', 'human': 'uncertain',
                  'judge': 'uncertain'} for i in range(6)]
        v3 = ([{'case_id': 'v%d' % i, 'split': 'frozen_test', 'human': 'pass',
                'judge': v3_judge_first if i < 2 else 'pass'} for i in range(6)]
              + [{'case_id': 'u%d' % i, 'split': 'frozen_test', 'human': 'uncertain',
                  'judge': 'uncertain'} for i in range(6)])
        b1, f1, g1 = batch_freeze('orig', orig, orig)
        b2, f2, g2 = batch_freeze('p2dev', p2dev, p2dev)
        vb, vf, vg = batch_freeze('v3', v3, v3)
        cp = self._write(d, 'gate.json', cfg())
        return ['--gate-config', str(cp),
                '--dev-batch', 'orig=' + str(b1), '--dev-gold', 'orig=' + str(g1),
                '--dev-freeze', 'orig=' + str(f1),
                '--dev-batch', 'p2dev=' + str(b2), '--dev-gold', 'p2dev=' + str(g2),
                '--dev-freeze', 'p2dev=' + str(f2),
                '--v3-batch', str(vb), '--v3-gold', str(vg), '--v3-freeze', str(vf)]

    def test_main_pass_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            argv = self._fixture(d)
            out = Path(d) / 'out'
            self.assertEqual(main(argv + ['--output', str(out)]), 0)
            result = json.loads((out / 'p3.gate.json').read_text(encoding='utf-8'))
            self.assertEqual(result['gate']['verdict'], 'PASS')
            self.assertEqual(result['B'], 200)
            self.assertIn('pass_recall', result['v3']['ci95'])
            self.assertTrue((out / 'P3_GATE_SUMMARY.md').exists())

    def test_main_fail_v3_pass_recall(self):
        with tempfile.TemporaryDirectory() as d:
            argv = self._fixture(d, v3_judge_first='uncertain')
            out = Path(d) / 'out'
            self.assertEqual(main(argv + ['--output', str(out)]), 0)
            result = json.loads((out / 'p3.gate.json').read_text(encoding='utf-8'))
            self.assertEqual(result['gate']['verdict'], 'FAIL')

    def test_main_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            argv = self._fixture(d)
            out = Path(d) / 'out'
            out.mkdir()
            self.assertEqual(main(argv + ['--output', str(out)]), 3)

    def test_main_refuses_draft_config(self):
        with tempfile.TemporaryDirectory() as d:
            argv = self._fixture(d)
            cp = Path(d) / 'gate.json'
            cp.write_text(json.dumps(cfg(status='draft')), encoding='utf-8', newline='')
            self.assertEqual(main(argv + ['--output', str(Path(d) / 'out')]), 1)

    def test_main_refuses_protocol_drift(self):
        with tempfile.TemporaryDirectory() as d:
            argv = self._fixture(d)
            bp = Path(d) / 'orig.batch.json'
            batch = json.loads(bp.read_text(encoding='utf-8'))
            batch['signature']['judge_version'] = '1.2.0'
            bp.write_text(json.dumps(batch), encoding='utf-8', newline='')
            self.assertEqual(main(argv + ['--output', str(Path(d) / 'out')]), 1)


if __name__ == '__main__':
    unittest.main()
