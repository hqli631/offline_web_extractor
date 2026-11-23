# -*- coding: utf-8 -*-
"""P-G G3 tests: pg page/cluster loading, freeze integrity, CLI discipline,
scorer verdicts on a hand-built consistent run (zero model calls)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import run_pg_repair as pgr
from tools import score_pg
from tools.node5_loop import sha256_json


def _assess(decision, score, severity):
    return {'decision': decision, 'dimensions': {'structure': {'score': score, 'severity': severity,
            'status': 'scored', 'reason': 'mock', 'evidence': []}}}


def _report(decision, score, severity):
    return {'mode': 'source_only', 'status': 'accepted', 'assessment': _assess(decision, score, severity),
            'usage': {'input_tokens': 100, 'output_tokens': 50, 'total_tokens': 150}}


class LoadingTests(unittest.TestCase):
    def test_load_pages_silver_and_features(self):
        pages, manifest = pgr.load_pg_pages()
        self.assertEqual(len(pages), 22)
        var = pages['pg_netbsd_index-var']
        self.assertIsNotNone(var['expected'])
        self.assertIn('NOT human gold', var['expected']['annotation_note'])
        self.assertIsNone(pages['pg_netbsd_index']['expected'])
        self.assertEqual(var['layout'], 'tag-swap-role-stripped')
        self.assertTrue(var['features'])

    def test_load_clusters_new_stratum(self):
        clusters = pgr.load_clusters()
        self.assertEqual(len(clusters), 5)
        for cid, cinfo in clusters.items():
            self.assertEqual(cinfo['rep'], cinfo['members'][0])
            self.assertEqual(cinfo['ref_ids'], cinfo['members'])


class FreezeTests(unittest.TestCase):
    def test_requires_quote(self):
        with self.assertRaises(ValueError):
            pgr.make_freeze(None)

    def test_roundtrip_clean(self):
        fz = pgr.make_freeze('test approval')
        self.assertEqual(pgr.check_freeze(fz), [])
        self.assertEqual(fz['freeze_version'], 'pg-repair-1')
        self.assertEqual(fz['budget']['token_cap'], 400000)
        self.assertEqual(fz['budget']['max_calls'], 30)

    def test_drift_detection(self):
        fz = pgr.make_freeze('test approval')
        fz['cluster_sha256'] = '0' * 64
        self.assertIn('cluster file drift', pgr.check_freeze(fz))
        fz2 = pgr.make_freeze('test approval')
        fz2['protocol']['rule_agent_sha256'] = '0' * 64
        self.assertTrue(any('rule_agent' in p for p in pgr.check_freeze(fz2)))
        fz3 = pgr.make_freeze('test approval')
        fz3['cases'][0]['source_sha256'] = '0' * 64
        self.assertTrue(any(p.startswith('source drift') for p in pgr.check_freeze(fz3)))


def _fake_run(fz, accepted):
    cases = {c['case_id']: c for c in fz['cases']}
    idx, var = 'pg_netbsd_index', 'pg_netbsd_index-var'
    repaired = {'title': 'T', 'blocks': [{'kind': 'paragraph', 'text': 'p1'}, {'kind': 'paragraph', 'text': 'p2'},
                                         {'kind': 'paragraph', 'text': 'p3'}]}
    trace = {'attempts': [{'executions': [{'id': var, 'execution': {'result': repaired}}]}],
             'runtime_accepted': True, 'selected_rule': {'version': 1, 'container_xpath': '//x', 'exclude_xpaths': []}}
    var_row = {'case_id': var, 'status': 'repaired', 'source_sha256': cases[var]['source_sha256'],
               'reuse': {'drift_reasons': ['no_shared_rule'], 'generalized_override': False},
               'baseline_decision': 'fail', 'baseline_defect_count': 1,
               'baseline_quality': {'block_text_recall': 0.0}, 'repaired_quality': {'block_text_recall': 1.0},
               'critic': _report('fail', 1, 'major'), 'rejudge': _report('uncertain', 4, 'none'),
               'repaired_candidate_sha256': sha256_json(repaired),
               'repair': {'triggered': True, 'trigger_reason': 'drift', 'reference_ids': [idx, var],
                          'trace': trace, 'prompt_audit': [{'passed': True, 'problems': []}],
                          'selected_rule': trace['selected_rule']}}
    idx_row = {'case_id': idx, 'status': 'no_repair_needed', 'source_sha256': cases[idx]['source_sha256'],
               'reuse': {'drift_reasons': ['no_shared_rule'], 'generalized_override': False},
               'baseline_decision': 'uncertain', 'baseline_defect_count': 0,
               'baseline_quality': None, 'repaired_quality': None, 'repair': {'triggered': False}}
    fb = {'attempted': True, 'accepted': accepted,
          'events': [{'member_id': var, 'accepted': accepted, 'programmatic_improved': True,
                      'generalizes': accepted, 'validation': [], 'blocked_reason': None if accepted else 'rule_does_not_generalize'}]}
    crow = {'cluster_id': 'pg-c4', 'rep_id': idx, 'multi_layout': True, 'layouts': ['natural', 'tag-swap-role-stripped'],
            'shared_rule': trace['selected_rule'], 'members': [idx_row, var_row], 'feedback': fb,
            'reuse_recovery': [var] if accepted else [], 'member_rule_cache': {var: trace['selected_rule']},
            'amortization': {'rule_generation_calls': 1, 'recovered_members': 1 if accepted else 0,
                             'calls_per_recovered': 1.0 if accepted else None}}
    return {'clusters': [crow], 'budget': {'used': 1000, 'calls': 3}}


class ScorerTests(unittest.TestCase):
    def test_real_template_signal(self):
        fz = pgr.make_freeze('test approval')
        result = score_pg.score_run(_fake_run(fz, True), fz, 'f' * 64)
        self.assertEqual(result['verdict'], 'REAL_TEMPLATE_SIGNAL')
        self.assertTrue(all(result['success_checks'].values()))
        self.assertEqual(result['metrics']['multi_layout_feedback_accepted'], 1)
        self.assertEqual(result['metrics']['paired_n'], 1)
        self.assertEqual(result['metrics']['improved'], 1)

    def test_no_signal_when_blocked(self):
        fz = pgr.make_freeze('test approval')
        result = score_pg.score_run(_fake_run(fz, False), fz, 'f' * 64)
        self.assertEqual(result['verdict'], 'NO_REAL_TEMPLATE_SIGNAL')
        self.assertFalse(result['success_checks']['multi_layout_feedback_accepted_ge'])


class CliTests(unittest.TestCase):
    def test_freeze_discipline(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'outputs') as td:
            fp = Path(td) / 'freeze.json'
            self.assertEqual(pgr.main(['--freeze', '--freeze-path', str(fp), '--approval-quote', 'test']), 0)
            self.assertEqual(pgr.main(['--freeze', '--freeze-path', str(fp), '--approval-quote', 'test']), 3)
            self.assertEqual(pgr.main(['--freeze', '--freeze-path', str(Path(td) / 'f2.json')]), 1)
            out = Path(td) / 'run.json'
            self.assertEqual(pgr.main(['--run', '--output', str(out), '--freeze-path', str(Path(td) / 'missing.json')]), 1)


if __name__ == '__main__':
    unittest.main()
