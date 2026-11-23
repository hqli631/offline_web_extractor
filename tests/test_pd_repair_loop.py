# -*- coding: utf-8 -*-
"""Offline tests for P-D repair->feedback loop (no model calls; mocks for orchestration)."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import run_pd_repair_loop as pd
from tools import score_pd

ROOT = Path(__file__).resolve().parents[1]


def _assessment(decision, comp_score=0, comp_sev='critical'):
    dims = {'completeness': {'score': comp_score, 'severity': comp_sev, 'status': 'scored', 'reason': 'r', 'evidence': []},
            'cleanliness': {'score': 4, 'severity': 'none', 'status': 'scored', 'reason': '', 'evidence': []},
            'structure': {'score': 4, 'severity': 'none', 'status': 'scored', 'reason': '', 'evidence': []},
            'title': {'score': 4, 'severity': 'none', 'status': 'scored', 'reason': '', 'evidence': []},
            'format': {'score': None, 'severity': 'none', 'status': 'not_applicable', 'reason': '', 'evidence': []}}
    return {'status': 'accepted', 'mode': 'source_only', 'assessment': {'decision': decision, 'dimensions': dims},
            'usage': {'total_tokens': 1000}}


def _trace(rule, blocks):
    return {'runtime_accepted': True, 'selected_rule': rule,
            'attempts': [{'number': 1, 'usage': {'total_tokens': 100},
                          'executions': [{'execution': {'result': {'title': 'T', 'blocks': blocks}}}]}]}


class PureFunctionsTest(unittest.TestCase):
    def test_load_corpus(self):
        pages = pd.load_corpus()
        self.assertEqual(len(pages), 5)
        self.assertIn('role-drift', pages)
        self.assertTrue(pages['reference']['features'])

    def test_cluster_groups(self):
        clusters = pd.cluster_groups(pd.load_corpus())
        self.assertEqual(clusters['reference-layout']['rep'], 'reference')
        self.assertEqual(clusters['reference-layout']['members'], ['class-drift', 'reference', 'role-drift'])

    def test_quality(self):
        ex = {'title': 'T', 'blocks': [{'text': 'a'}, {'text': 'b'}]}
        ee = {'title': 'T', 'blocks': [{'text': 'a'}, {'text': 'b'}, {'text': 'c'}]}
        q = pd.quality(ex, ee)
        self.assertEqual(q['block_text_recall'], 0.666667)
        self.assertEqual(q['block_text_precision'], 1.0)
        self.assertFalse(q['blocks_exact'])

    def test_freeze_check_happy(self):
        fz = pd.make_freeze()
        self.assertEqual(pd.check_freeze(fz), [])

    def test_freeze_check_drift(self):
        fz = pd.make_freeze()
        fz['protocol']['judge_module_sha256'] = 'deadbeef'
        self.assertTrue(any('rubrics_judge_v141' in p for p in pd.check_freeze(fz)))

    def test_validate_feedback_blocked_member_specific(self):
        pages = pd.load_corpus()
        rule = {'version': 1, 'container_xpath': "//*[@role='article']", 'exclude_xpaths': []}
        ok, checks = pd.validate_feedback(rule, 'reference', ['class-drift', 'role-drift'], pages,
                                          {'reference': 1.0, 'class-drift': 1.0, 'role-drift': 0.0})
        self.assertFalse(ok)  # role=article fails on reference (role=main)
        ref = next(c for c in checks if c['case_id'] == 'reference')
        self.assertFalse(ref['pass'])

    def test_validate_feedback_generalizes_union(self):
        pages = pd.load_corpus()
        rule = {'version': 1, 'container_xpath': "//*[@role='main'] | //*[@role='article']", 'exclude_xpaths': []}
        ok, checks = pd.validate_feedback(rule, 'reference', ['class-drift', 'role-drift'], pages,
                                          {'reference': 1.0, 'class-drift': 1.0, 'role-drift': 0.0})
        self.assertTrue(ok)


class OrchestrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.fz = pd.make_freeze()
        self.pages = pd.load_corpus()
        from src.webextractor.rule_cache import ClusterRuleCache
        self.cache = ClusterRuleCache(drift_threshold=0.7)
        rep = self.pages['reference']
        self.cache.derive_and_cache('reference-layout', 'reference', rep['source'], rep['features'])
        self.guard = pd.BudgetGuard(300000, 16000, 8000)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_role_drift_trigger_repair(self):
        rule = {'version': 1, 'container_xpath': "//*[@role='article']", 'exclude_xpaths': []}
        blocks = self.pages['role-drift']['expected']['blocks']
        with mock.patch.object(pd.j141, 'run_judge', side_effect=[_assessment('fail'), _assessment('uncertain', 4, 'none')]), \
             mock.patch.object(pd, 'run_agent', return_value=_trace(rule, blocks)):
            row = pd.run_member('reference-layout', 'reference', 'role-drift', self.pages,
                                self.cache, None, None, self.guard, self.fz)
        self.assertEqual(row['status'], 'repaired')
        self.assertTrue(row['repair']['triggered'])
        self.assertEqual(row['repaired_quality']['block_text_recall'], 1.0)
        self.assertEqual(row['baseline_quality']['block_text_recall'], 0.0)

    def test_class_drift_no_repair(self):
        with mock.patch.object(pd.j141, 'run_judge', return_value=_assessment('uncertain', 4, 'none')):
            row = pd.run_member('reference-layout', 'reference', 'class-drift', self.pages,
                                self.cache, None, None, self.guard, self.fz)
        self.assertEqual(row['status'], 'no_repair_needed')
        self.assertFalse(row['repair']['triggered'])

    def test_cluster_feedback_blocked_but_member_cached(self):
        rule = {'version': 1, 'container_xpath': "//*[@role='article']", 'exclude_xpaths': []}
        blocks = self.pages['role-drift']['expected']['blocks']
        cinfo = {'rep': 'reference', 'members': ['role-drift']}
        with mock.patch.object(pd.j141, 'run_judge', side_effect=[_assessment('fail'), _assessment('uncertain', 4, 'none')]), \
             mock.patch.object(pd, 'run_agent', return_value=_trace(rule, blocks)):
            crow = pd.run_cluster('reference-layout', cinfo, self.pages, None, None, self.guard, self.fz)
        self.assertTrue(crow['feedback']['attempted'])
        self.assertFalse(crow['feedback']['accepted'])
        self.assertEqual(crow['feedback']['detail']['blocked_reason'], 'rule_does_not_generalize')
        self.assertIn('role-drift', crow['member_rule_cache'])

    def test_cluster_feedback_accepted_union(self):
        rule = {'version': 1, 'container_xpath': "//*[@role='main'] | //*[@role='article']", 'exclude_xpaths': []}
        blocks = self.pages['role-drift']['expected']['blocks']
        cinfo = {'rep': 'reference', 'members': ['role-drift']}
        with mock.patch.object(pd.j141, 'run_judge', side_effect=[_assessment('fail'), _assessment('uncertain', 4, 'none')]), \
             mock.patch.object(pd, 'run_agent', return_value=_trace(rule, blocks)):
            crow = pd.run_cluster('reference-layout', cinfo, self.pages, None, None, self.guard, self.fz)
        self.assertTrue(crow['feedback']['accepted'])
        self.assertTrue(crow['feedback']['detail']['rereuse'][0]['reuse'])


class ScorerTest(unittest.TestCase):
    def test_score_verdict_benefit(self):
        fz = pd.make_freeze()
        run = {'clusters': [{'cluster_id': 'reference-layout', 'rep_id': 'reference',
                             'shared_rule': None, 'member_rule_cache': {},
                             'feedback': {'attempted': True, 'accepted': False, 'detail': {'blocked_reason': 'rule_does_not_generalize'}},
                             'members': [{'case_id': 'role-drift', 'status': 'repaired',
                                          'source_sha256': fz['cases'][2]['source_sha256'] if fz['cases'][2]['case_id'] == 'role-drift' else next(c['source_sha256'] for c in fz['cases'] if c['case_id'] == 'role-drift'),
                                          'reuse': {'drift_reasons': ['rule_failure']},
                                          'baseline_decision': 'fail', 'baseline_defect_count': 1,
                                          'repair': {'triggered': True, 'trigger_reason': 'drift', 'prompt_audit': [{'passed': True}],
                                                     'trace': _trace({'version': 1, 'container_xpath': "//*[@role='article']", 'exclude_xpaths': []}, [{'text': 'x'}])},
                                          'repaired_candidate_sha256': pd.sha256_json({'title': 'T', 'blocks': [{'text': 'x'}]}),
                                          'critic': _assessment('fail'), 'rejudge': _assessment('uncertain', 4, 'none'),
                                          'baseline_quality': {'block_text_recall': 0.0}, 'repaired_quality': {'block_text_recall': 1.0}}]}],
               'budget': {'used': 100}}
        rep = score_pd.score_run(run, fz, 'freezesha')
        self.assertEqual(rep['metrics']['paired_n'], 1)
        self.assertEqual(rep['metrics']['improved'], 1)
        self.assertTrue(rep['metrics']['drift_recovery']['recovered'])
        self.assertEqual(rep['verdict'], 'REPAIR_BENEFIT_SIGNAL')

    def test_cli_overwrite_refusal(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            out = tmp / 'o.json'
            out.write_text('{}', encoding='utf-8')
            rc = score_pd.main(['--run', str(out), '--output', str(out)])
            self.assertEqual(rc, 3)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
