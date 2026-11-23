# -*- coding: utf-8 -*-
"""P-D2 tests: corpus v2 integrity, freeze, generalized reuse semantics,
mocked cluster-generalized repair orchestration, scorer metrics, CLI discipline.
Zero model calls; rule execution uses the real trusted executor on tiny fixtures.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import run_pd2_generalize as pd2
from tools import score_pd2
from tools.node5_loop import sha256_bytes
from src.webextractor.rule_cache import ClusterRuleCache

UNION_RULE = {'version': 1,
              'container_xpath': "//*[@role='main'] | //*[@role='article'] | //*[@id='article-body'] | //section[contains(concat(' ', normalize-space(@class), ' '), ' article-shell-v4 ')]",
              'exclude_xpaths': []}


def _assessment(decision, score, severity):
    return {'decision': decision,
            'dimensions': {'structure': {'score': score, 'severity': severity, 'status': 'scored',
                                         'reason': 'mock', 'evidence': []}}}


def _judge_report(decision, score, severity):
    return {'mode': 'source_only', 'status': 'accepted',
            'assessment': _assessment(decision, score, severity),
            'usage': {'input_tokens': 100, 'output_tokens': 50, 'total_tokens': 150}}


def _mock_judge(source, candidate, provider, **kwargs):
    blocks = candidate.get('blocks') or []
    if len(blocks) >= 3:
        return _judge_report('uncertain', 4, 'none')
    return _judge_report('fail', 1, 'major')


class _RuleProvider:
    model = 'mock-rule'

    def __init__(self, rule):
        self.rule = rule
        self.prompts = []

    def generate(self, prompt, *, timeout_seconds, max_output_tokens):
        self.prompts.append(prompt)
        return {'content': json.dumps(self.rule),
                'usage': {'input_tokens': 200, 'output_tokens': 60, 'total_tokens': 260}}


class CorpusV2Tests(unittest.TestCase):
    def test_original_fixtures_byte_identical(self):
        orig = json.loads((ROOT / 'samples/dom_similarity.controlled.json').read_text(encoding='utf-8'))
        v2 = json.loads((ROOT / pd2.CORPUS_REL).read_text(encoding='utf-8'))
        v2_by_id = {p['id']: p for p in v2['pages']}
        for p in orig['pages']:
            q = v2_by_id[p['id']]
            self.assertEqual(q['sha256'], p['sha256'])
            self.assertEqual(sha256_bytes((ROOT / 'samples' / p['html']).read_bytes()), p['sha256'])

    def test_v2_pages_groups_layouts(self):
        pages = pd2.load_corpus()
        self.assertEqual(len(pages), 7)
        clusters = pd2.cluster_groups(pages)
        self.assertEqual(sorted(clusters['reference-layout']['members']),
                         ['class-drift', 'id-drift', 'reference', 'role-drift', 'section-drift'])
        self.assertEqual(pages['id-drift']['layout'], 'id-article-body-div')
        self.assertEqual(pages['section-drift']['layout'], 'section-v4')

    def test_builder_v2_rerun_deterministic(self):
        sys.path.insert(0, str(ROOT / 'samples' / 'drift_lab'))
        try:
            import build_fixtures_v2
            build_fixtures_v2.main()
        finally:
            sys.path.remove(str(ROOT / 'samples' / 'drift_lab'))


class FreezeTests(unittest.TestCase):
    def test_freeze_requires_approval_quote(self):
        with self.assertRaises(ValueError):
            pd2.make_freeze(None)
        with self.assertRaises(ValueError):
            pd2.make_freeze('   ')

    def test_freeze_roundtrip_clean(self):
        fz = pd2.make_freeze('test approval quote')
        self.assertEqual(pd2.check_freeze(fz), [])
        self.assertEqual(fz['freeze_version'], 'pd2-1')
        self.assertEqual(fz['budget']['max_calls'], 20)
        self.assertEqual(fz['budget']['token_cap'], 200000)

    def test_freeze_detects_drift(self):
        fz = pd2.make_freeze('test approval quote')
        fz['corpus_sha256'] = '0' * 64
        self.assertIn('corpus drift', pd2.check_freeze(fz))
        fz2 = pd2.make_freeze('test approval quote')
        fz2['cases'][0]['source_sha256'] = '0' * 64
        self.assertTrue(any(p.startswith('source drift') for p in pd2.check_freeze(fz2)))
        fz3 = pd2.make_freeze('test approval quote')
        fz3['protocol']['rule_agent_sha256'] = '0' * 64
        self.assertTrue(any('rule_agent' in p for p in pd2.check_freeze(fz3)))


class ReuseSemanticsTests(unittest.TestCase):
    def setUp(self):
        self.pages = pd2.load_corpus()
        self.cache = ClusterRuleCache(drift_threshold=0.7)
        rep = self.pages['reference']
        self.cache.derive_and_cache('reference-layout', 'reference', rep['source'], rep['features'])

    def test_v0_no_override(self):
        pg = self.pages['section-drift']
        rr = pd2.reuse_pd2(self.cache, 'reference-layout', 'section-drift', pg['source'], pg['features'])
        self.assertFalse(rr['reuse'])
        self.assertFalse(rr['generalized_override'])
        self.assertIn('rule_failure', rr['drift_reasons'])

    def test_validated_generalized_rule_overrides_fingerprint_drift(self):
        entry = self.cache.entries['reference-layout']
        entry['rule'] = UNION_RULE
        entry['generalized_validated'] = True
        pg = self.pages['section-drift']
        rr = pd2.reuse_pd2(self.cache, 'reference-layout', 'section-drift', pg['source'], pg['features'])
        self.assertTrue(rr['reuse'])
        self.assertTrue(rr['generalized_override'])
        self.assertEqual(rr['drift_reasons'], [])
        self.assertEqual(rr['block_count'], 3)

    def test_rule_failure_never_overridden(self):
        entry = self.cache.entries['reference-layout']
        entry['generalized_validated'] = True  # rule still v0 role=main
        pg = self.pages['id-drift']
        rr = pd2.reuse_pd2(self.cache, 'reference-layout', 'id-drift', pg['source'], pg['features'])
        self.assertFalse(rr['reuse'])
        self.assertFalse(rr['generalized_override'])
        self.assertIn('rule_failure', rr['drift_reasons'])


class GuardTests(unittest.TestCase):
    def test_max_calls_ceiling(self):
        g = pd2.Pd2Guard(100000, 2)
        self.assertTrue(g.allow('judge', 'a'))
        g.record_call()
        self.assertTrue(g.allow('rule', 'a'))
        g.record_call()
        self.assertFalse(g.allow('judge', 'b'))
        self.assertEqual(g.skipped[-1]['reason'], 'max_calls')


def _run_reference_layout(rule=UNION_RULE, block_feedback=False):
    pages = pd2.load_corpus()
    fz = pd2.make_freeze('test approval quote')
    guard = pd2.Pd2Guard(200000, 20)
    rp = _RuleProvider(rule)
    cinfo = fz['clusters']['reference-layout']
    with mock.patch.object(pd2.j141, 'run_judge', side_effect=_mock_judge):
        if block_feedback:
            with mock.patch.object(pd2, 'validate_feedback', return_value=(False, [])):
                crow = pd2.run_cluster_pd2('reference-layout', cinfo, pages, None, rp, guard, fz)
        else:
            crow = pd2.run_cluster_pd2('reference-layout', cinfo, pages, None, rp, guard, fz)
    return crow, fz, pages


class OrchestrationTests(unittest.TestCase):
    def test_generalized_repair_refs_and_inline_feedback(self):
        crow, fz, pages = _run_reference_layout()
        statuses = {m['case_id']: m['status'] for m in crow['members']}
        self.assertEqual(statuses, {'class-drift': 'no_repair_needed', 'id-drift': 'repaired',
                                    'reference': 'no_repair_needed', 'role-drift': 'no_repair_needed',
                                    'section-drift': 'no_repair_needed'})
        idrow = next(m for m in crow['members'] if m['case_id'] == 'id-drift')
        self.assertEqual(idrow['repair']['reference_ids'], sorted(crow['ref_ids']))
        self.assertEqual(len(idrow['repair']['reference_ids']), 5)
        self.assertTrue(crow['multi_layout'])
        self.assertTrue(crow['feedback']['accepted'])
        self.assertEqual(len(crow['feedback']['events']), 1)
        self.assertEqual(crow['shared_rule'], UNION_RULE)
        self.assertEqual(crow['reuse_recovery'], ['id-drift', 'role-drift', 'section-drift'])
        self.assertEqual(crow['amortization']['rule_generation_calls'], 1)
        self.assertAlmostEqual(crow['amortization']['calls_per_recovered'], 0.3333, places=3)
        self.assertTrue(crow['final_reuse']['section-drift']['generalized_override'])
        self.assertEqual(crow['final_reuse']['section-drift']['quality']['block_text_recall'], 1.0)

    def test_multi_page_prompt_audit_passed(self):
        crow, _, _ = _run_reference_layout()
        idrow = next(m for m in crow['members'] if m['case_id'] == 'id-drift')
        self.assertTrue(idrow['repair']['prompt_audit'])
        for pa in idrow['repair']['prompt_audit']:
            self.assertTrue(pa['passed'], pa['problems'])
        prompt = idrow['repair']['audit_log'][0]['prompt']
        self.assertEqual(len(prompt['reference_pages']), 5)

    def test_feedback_blocked_retains_member_rule(self):
        crow, _, _ = _run_reference_layout(block_feedback=True)
        self.assertTrue(crow['feedback']['attempted'])
        self.assertFalse(crow['feedback']['accepted'])
        for ev in crow['feedback']['events']:
            self.assertEqual(ev['blocked_reason'], 'rule_does_not_generalize')
        self.assertIn('id-drift', crow['member_rule_cache'])
        self.assertEqual(crow['shared_rule']['container_xpath'], "//*[@role='main']")
        self.assertEqual(crow['reuse_recovery'], [])
        self.assertIsNone(crow['amortization']['calls_per_recovered'])


class ScorerTests(unittest.TestCase):
    def test_generalization_signal(self):
        crow, fz, _ = _run_reference_layout()
        run = {'clusters': [crow], 'budget': {'used': 1000, 'calls': 7}}
        result = score_pd2.score_run(run, fz, 'f' * 64)
        self.assertEqual(result['verdict'], 'GENERALIZATION_SIGNAL')
        self.assertTrue(all(result['success_checks'].values()))
        self.assertEqual(result['metrics']['multi_layout_feedback_accepted'], 1)
        self.assertEqual(result['metrics']['reuse_recovery_total'], 3)
        self.assertEqual(result['metrics']['paired_n'], 1)
        self.assertEqual(result['metrics']['improved'], 1)

    def test_no_signal_when_feedback_blocked(self):
        crow, fz, _ = _run_reference_layout(block_feedback=True)
        run = {'clusters': [crow], 'budget': {'used': 1000, 'calls': 12}}
        result = score_pd2.score_run(run, fz, 'f' * 64)
        self.assertEqual(result['verdict'], 'NO_GENERALIZATION_SIGNAL')
        self.assertFalse(result['success_checks']['multi_layout_feedback_accepted_ge'])
        self.assertFalse(result['success_checks']['reuse_recovery_after_feedback_ge'])


class CliTests(unittest.TestCase):
    def test_freeze_and_overwrite_refusal(self):
        with tempfile.TemporaryDirectory() as td:
            fp = Path(td) / 'pd2.freeze.test.json'
            rc = pd2.main(['--freeze', '--freeze-path', str(fp), '--approval-quote', 'test approval'])
            self.assertEqual(rc, 0)
            self.assertTrue(fp.exists())
            rc2 = pd2.main(['--freeze', '--freeze-path', str(fp), '--approval-quote', 'test approval'])
            self.assertEqual(rc2, 3)

    def test_freeze_missing_quote_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fp = Path(td) / 'pd2.freeze.test.json'
            rc = pd2.main(['--freeze', '--freeze-path', str(fp)])
            self.assertEqual(rc, 1)
            self.assertFalse(fp.exists())

    def test_run_requires_freeze_and_fresh_output(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'run.json'
            rc = pd2.main(['--run', '--output', str(out), '--freeze-path', str(Path(td) / 'missing.json')])
            self.assertEqual(rc, 1)
            out.write_text('{}', encoding='utf-8')
            rc2 = pd2.main(['--run', '--output', str(out), '--freeze-path', str(Path(td) / 'missing.json')])
            self.assertEqual(rc2, 3)


if __name__ == '__main__':
    unittest.main()
