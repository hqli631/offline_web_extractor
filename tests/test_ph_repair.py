# -*- coding: utf-8 -*-
"""P-H H1 tests: GATE-1 trigger / GATE-2 retention with mocked judge+agent
(zero model calls), retention metric, freeze + CLI discipline."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import run_ph_repair as ph
from tools.run_pd2_generalize import Pd2Guard
from src.webextractor.rule_cache import ClusterRuleCache
from src.webextractor.dom_similarity import structural_features
from tools.node5_loop import sha256_bytes

HTML = b'<html><body><article><p>alpha</p><p>beta</p><p>gamma</p></article></body></html>'
BASE = {'title': 't', 'blocks': [{'text': 'alpha'}, {'text': 'beta'}, {'text': 'gamma'}]}
FREEZE = {'protocol': {'max_source_chars': 20000, 'max_output_tokens': 2200, 'timeout_seconds': 90,
                       'rule_max_attempts': 2, 'execution_timeout': 5.0, 'total_timeout': 120.0,
                       'rule_max_output_tokens': 1024, 'evidence_chars': 16000},
          'params': {'drift_threshold': 0.7}}


def _report(decision, score, severity):
    return {'mode': 'source_only', 'status': 'accepted', 'judge_version': '1.4.1',
            'assessment': {'decision': decision,
                           'dimensions': {'structure': {'score': score, 'severity': severity,
                                                        'status': 'scored', 'reason': 'mock', 'evidence': []}}},
            'usage': {'input_tokens': 100, 'output_tokens': 50, 'total_tokens': 150}}


def _reuse(drift=True, extraction=None):
    return {'reuse': not drift, 'fallback': drift, 'drift': drift,
            'drift_reasons': ['fingerprint_drift'] if drift else [],
            'fingerprint_similarity': 0.5 if drift else 1.0,
            'rule_status': 'ok', 'final_status': 'ok', 'block_count': 3,
            'generalized_override': False, 'extraction': extraction or dict(BASE)}


def _trace(member_id, blocks):
    rule = {'version': 1, 'container_xpath': '//article', 'exclude_xpaths': []}
    return {'runtime_accepted': True, 'selected_rule': rule,
            'attempts': [{'number': 1, 'usage': {'total_tokens': 260}, 'error': None,
                          'executions': [{'id': member_id,
                                          'execution': {'result': {'title': 't', 'blocks': blocks}}}]}]}


def _pages(expected=None):
    feats = structural_features(HTML, 'suffix-presence')
    return {'m1': {'source': HTML, 'source_sha256': sha256_bytes(HTML), 'features': feats,
                   'expected': expected, 'layout': 'natural'}}


def _run_member(critic_report, repaired_blocks, expected=None, drift=True):
    pages = _pages(expected)
    cache = ClusterRuleCache(0.7)
    guard = Pd2Guard(10 ** 9, 20)
    judge_calls = []

    def judge(source, candidate, provider, **kw):
        judge_calls.append(candidate)
        return critic_report if len(judge_calls) == 1 else _report('uncertain', 4, 'none')

    with mock.patch.object(ph, 'reuse_pd2', return_value=_reuse(drift)), \
         mock.patch.object(ph.j141, 'run_judge', side_effect=judge), \
         mock.patch.object(ph, 'run_agent', return_value=_trace('m1', repaired_blocks)) as agent:
        row = ph.run_member_ph('c', 'm1', 'm1', ['m1'], pages, cache, None, None, guard, FREEZE)
    return row, len(judge_calls), agent.call_count


class Gate1Tests(unittest.TestCase):
    def test_good_baseline_with_drift_skipped(self):
        row, judges, agents = _run_member(_report('uncertain', 4, 'none'), [])
        self.assertEqual(row['status'], 'no_repair_needed')
        self.assertTrue(row['repair']['note'].startswith('v1.1 GATE-1'))
        self.assertEqual(agents, 0)
        self.assertEqual(judges, 1)

    def test_fail_triggers(self):
        row, judges, agents = _run_member(_report('fail', 1, 'major'),
                                          [{'text': 'alpha'}, {'text': 'beta'}, {'text': 'gamma'}])
        self.assertTrue(row['repair']['triggered'])
        self.assertEqual(agents, 1)
        self.assertEqual(row['status'], 'repaired')

    def test_silver_low_triggers(self):
        expected = {'title': 't', 'blocks': [{'text': x} for x in ('alpha', 'beta', 'gamma', 'delta')]}
        row, judges, agents = _run_member(_report('uncertain', 4, 'none'),
                                          [{'text': x} for x in ('alpha', 'beta', 'gamma', 'delta')],
                                          expected=expected)
        self.assertTrue(row['repair']['triggered'])
        self.assertEqual(agents, 1)

    def test_minor_only_no_silver_skipped(self):
        row, _, agents = _run_member(_report('uncertain', 3, 'minor'), [])
        self.assertEqual(row['status'], 'no_repair_needed')
        self.assertEqual(agents, 0)


class Gate2Tests(unittest.TestCase):
    EXPECTED = {'title': 't', 'blocks': [{'text': x} for x in ('alpha', 'beta', 'gamma', 'delta')]}

    def test_overexclusion_rejected_no_rejudge(self):
        row, judges, agents = _run_member(_report('uncertain', 4, 'none'), [{'text': 'alpha'}],
                                          expected=self.EXPECTED)
        self.assertEqual(row['status'], 'repair_rejected_retention')
        self.assertLess(row['repair']['retention_recall'], 0.9)
        self.assertEqual(judges, 1)  # critic only, no rejudge

    def test_retention_pass_rejudges(self):
        row, judges, _ = _run_member(_report('uncertain', 4, 'none'),
                                     [{'text': x} for x in ('alpha', 'beta', 'gamma')],
                                     expected=self.EXPECTED)
        self.assertEqual(row['status'], 'repaired')
        self.assertEqual(row['repair']['retention_recall'], 1.0)
        self.assertEqual(judges, 2)

    def test_fail_baseline_no_retention_constraint(self):
        row, judges, _ = _run_member(_report('fail', 1, 'major'), [{'text': 'rewritten'}])
        self.assertEqual(row['status'], 'repaired')
        self.assertNotIn('retention_recall', row['repair'])
        self.assertEqual(judges, 2)


class RetentionMetricTests(unittest.TestCase):
    def test_empty_baseline(self):
        self.assertEqual(ph._text_retention({'blocks': []}, {'blocks': []}), 1.0)

    def test_counter_duplicates(self):
        b = {'blocks': [{'text': 'a'}, {'text': 'a'}]}
        r = {'blocks': [{'text': 'a'}]}
        self.assertEqual(ph._text_retention(b, r), 0.5)


class DisciplineTests(unittest.TestCase):
    def test_freeze_requires_quote(self):
        with self.assertRaises(ValueError):
            ph.make_freeze(None)

    def test_freeze_and_check(self):
        fz = ph.make_freeze('unit-test approval')
        self.assertEqual(fz['freeze_version'], 'ph-repair-1')
        self.assertEqual(fz['budget']['max_calls'], 20)
        self.assertEqual(fz['budget']['token_cap'], 300000)
        self.assertEqual(ph.check_freeze(fz), [])
        bad = dict(fz)
        bad['plan_sha256'] = '0' * 64
        self.assertTrue(any('plan drift' in p for p in ph.check_freeze(bad)))

    def test_cli_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'x.json'
            out.write_text('{}', encoding='utf-8')
            self.assertEqual(ph.main(['--run', '--output', str(out)]), 3)
            fz = Path(td) / 'f.json'
            fz.write_text('{}', encoding='utf-8')
            self.assertEqual(ph.main(['--freeze', '--freeze-path', str(fz), '--approval-quote', 'x']), 3)


if __name__ == '__main__':
    unittest.main()
