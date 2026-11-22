# -*- coding: utf-8 -*-
"""Node 5 scorer tests: frozen classification, bootstrap determinism, integrity
fail-closed, verdict logic, CLI overwrite refusal. Zero model calls."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.webextractor.extractor import extract_html
import tools.node5_loop as n5
import tools.score_node5 as sc

DIMS = ('completeness', 'cleanliness', 'structure', 'title', 'format')


def mk_dims(**overrides):
    dims = {name: {'score': 4, 'status': 'scored', 'severity': 'none', 'reason': 'ok', 'evidence': []}
            for name in DIMS}
    for name, upd in overrides.items():
        dims[name].update(upd)
    return dims


def assess(decision='uncertain', dims=None):
    return {'decision': decision, 'dimensions': dims if dims is not None else mk_dims()}


def mk_report(decision='uncertain', dims=None, status='accepted', mode='source_only', tokens=1000):
    return {'status': status, 'mode': mode, 'assessment': assess(decision, dims),
            'usage': {'input_tokens': tokens - 100, 'output_tokens': 100, 'total_tokens': tokens}}


def clean_prompt():
    return {'instruction': 'x', 'reference_pages': [{'id': 'c', 'source': '<html></html>'}],
            'previous_attempts': [], 'critic_feedback': {'decision': 'fail', 'defects': [], 'guidance': 'adjust xpaths'},
            'baseline_extraction_preview': {'title': 't', 'block_count': 1, 'body_preview': 'b'}}


def mk_trace(result):
    return {'status': 'runtime_accepted', 'runtime_accepted': True,
            'selected_rule': {'version': 1, 'container_xpath': '//article', 'exclude_xpaths': []},
            'attempts': [{'number': 1, 'usage': {'total_tokens': 500},
                          'executions': [{'id': 'c', 'execution': {'status': 'ok', 'result': result}}]}]}


class ClassificationTests(unittest.TestCase):
    def test_improved_decision(self):
        before = assess('fail', mk_dims(cleanliness={'score': 2, 'severity': 'major'}))
        after = assess('uncertain', mk_dims(cleanliness={'score': 3, 'severity': 'minor'}))
        p = sc.classify_pair(before, after)
        self.assertEqual(p['category'], 'improved')
        self.assertEqual(p['delta'], 1)

    def test_improved_score_same_decision(self):
        before = assess('uncertain', mk_dims(cleanliness={'score': 3, 'severity': 'minor'}))
        after = assess('uncertain')
        p = sc.classify_pair(before, after)
        self.assertEqual(p['category'], 'improved')
        self.assertTrue(p['score_comparable'])
        self.assertEqual(p['delta'], 1)

    def test_regressed_new_severe_same_decision(self):
        before = assess('fail', mk_dims(cleanliness={'score': 2, 'severity': 'major'}))
        after = assess('fail', mk_dims(cleanliness={'score': 2, 'severity': 'major'},
                                     structure={'score': 2, 'severity': 'major'}))
        p = sc.classify_pair(before, after)
        self.assertEqual(p['category'], 'regressed')
        self.assertEqual(p['new_severe_dimensions'], ['structure'])

    def test_regressed_decision(self):
        before = assess('uncertain', mk_dims(cleanliness={'score': 3, 'severity': 'minor'}))
        after = assess('fail', mk_dims(cleanliness={'score': 2, 'severity': 'major'}))
        self.assertEqual(sc.classify_pair(before, after)['category'], 'regressed')

    def test_no_effect_identical(self):
        a = assess('uncertain', mk_dims(cleanliness={'score': 3, 'severity': 'minor'}))
        p = sc.classify_pair(a, assess('uncertain', mk_dims(cleanliness={'score': 3, 'severity': 'minor'})))
        self.assertEqual(p['category'], 'no_effect')
        self.assertEqual(p['delta'], 0)

    def test_other_change_score_decline_without_new_severe(self):
        before = assess('uncertain', mk_dims(cleanliness={'score': 3, 'severity': 'minor'}))
        after = assess('uncertain', mk_dims(cleanliness={'score': 2, 'severity': 'minor'}))
        p = sc.classify_pair(before, after)
        self.assertEqual(p['category'], 'other_change')
        self.assertEqual(p['delta'], -1)

    def test_score_path_requires_comparable_scored_set(self):
        before = assess('uncertain', mk_dims(format={'score': None, 'status': 'not_applicable', 'severity': 'none'},
                                             cleanliness={'score': 3, 'severity': 'minor'}))
        after = assess('uncertain')
        p = sc.classify_pair(before, after)
        self.assertFalse(p['score_comparable'])
        self.assertEqual(p['category'], 'other_change')

    def test_new_severe_takes_priority_over_score_gain(self):
        before = assess('fail', mk_dims(cleanliness={'score': 2, 'severity': 'major'}))
        after = assess('fail', mk_dims(cleanliness={'score': 4, 'severity': 'none'},
                                     structure={'score': 2, 'severity': 'major'}))
        p = sc.classify_pair(before, after)
        self.assertEqual(p['category'], 'regressed')


class BootstrapTests(unittest.TestCase):
    def test_ci_deterministic_and_point(self):
        from tools.bootstrap_stats import bootstrap_ci
        recs = [{'delta': 1}, {'delta': 2}, {'delta': 3}]
        fn = lambda rs: sum(r['delta'] for r in rs) / len(rs)
        a = bootstrap_ci(recs, fn, B=1000, seed=20261119)
        b = bootstrap_ci(recs, fn, B=1000, seed=20261119)
        self.assertEqual(a, b)
        self.assertEqual(a['point'], 2.0)
        self.assertEqual(a['n'], 3)


def _case_row(fz, case_id, status, critic, rejudge=None, triggered=False, audit_prompt=None, bad_sha=False):
    fc = next(c for c in fz['cases'] if c['case_id'] == case_id)
    base = extract_html((n5.ROOT / fc['source']).read_bytes())
    baseline = {'title': base.title, 'blocks': base.to_dict()['blocks']}
    row = {'case_id': case_id, 'template': fc['template'], 'source_sha256': fc['source_sha256'],
           'baseline_candidate_sha256': n5.sha256_json(baseline), 'status': status,
           'critic': critic, 'repair': {'triggered': triggered}, 'calls': []}
    if status == 'repaired':
        row['rejudge'] = rejudge
        row['repaired_candidate_sha256'] = '0' * 64 if bad_sha else n5.sha256_json(baseline)
        row['repair']['trace'] = mk_trace(baseline)
        if audit_prompt is not None:
            row['repair']['audit_log'] = [{'prompt_sha256': n5.sha256_json(audit_prompt), 'prompt': audit_prompt}]
            row['repair']['prompt_audit'] = [n5.audit_repair_prompt(audit_prompt, critic)]
    return row


class ScoreRunTests(unittest.TestCase):
    def setUp(self):
        self.fz = n5.make_freeze()
        self.fz_sha = n5.sha256_json(self.fz)
        self.fail_critic = mk_report('fail', mk_dims(cleanliness={'score': 2, 'severity': 'major'}))
        self.good_rejudge = mk_report('uncertain', mk_dims(cleanliness={'score': 3, 'severity': 'minor'}))

    def score(self, rows):
        run = {'freeze_sha256': self.fz_sha, 'cases': rows, 'budget': {'cap': 220000, 'used': 2500, 'skipped': []}}
        return sc.score_run(run, self.fz, self.fz_sha)

    def test_end_to_end_benefit_signal(self):
        rows = [_case_row(self.fz, 'n5-appetite', 'repaired', self.fail_critic, self.good_rejudge,
                          triggered=True, audit_prompt=clean_prompt()),
                _case_row(self.fz, 'n5-iana', 'no_repair_needed', mk_report('uncertain'))]
        rep = self.score(rows)
        self.assertEqual(rep['verdict'], 'REPAIR_BENEFIT_SIGNAL')
        m = rep['metrics']
        self.assertEqual(m['paired_n'], 1)
        self.assertEqual(m['improved'], 1)
        self.assertEqual(m['improvement_rate'], 1.0)
        self.assertEqual(m['regression_rate'], 0.0)
        self.assertEqual(m['repair_trigger_rate'], 0.5)
        self.assertEqual(m['unnecessary_repair_count'], 0)
        self.assertEqual(m['mean_total_score_delta_ci95']['n'], 1)
        self.assertEqual(rep['audits'], {'prompts_audited': 1, 'failures': []})
        self.assertEqual(rep['candidate_integrity_problems'], [])
        self.assertIn('after', rep['per_case'][0]['side_check'])
        self.assertNotIn('side_check', rep['per_case'][1])

    def test_no_pairs_no_benefit(self):
        rep = self.score([_case_row(self.fz, 'n5-iana', 'no_repair_needed', mk_report('uncertain'))])
        self.assertEqual(rep['verdict'], 'NO_BENEFIT_SIGNAL')
        self.assertEqual(rep['metrics']['paired_n'], 0)
        self.assertIsNone(rep['metrics']['improvement_rate'])
        self.assertIsNone(rep['metrics']['mean_total_score_delta_ci95']['ci95'])

    def test_unnecessary_repair_fails_verdict(self):
        rows = [_case_row(self.fz, 'n5-appetite', 'repaired', mk_report('uncertain'), mk_report('uncertain'),
                          triggered=True, audit_prompt=clean_prompt())]
        rep = self.score(rows)
        self.assertEqual(rep['metrics']['unnecessary_repair_count'], 1)
        self.assertEqual(rep['verdict'], 'NO_BENEFIT_SIGNAL')

    def test_audit_failure_fails_verdict(self):
        bad = clean_prompt()
        bad['reference_pages'][0]['gold_blocks'] = []
        rows = [_case_row(self.fz, 'n5-appetite', 'repaired', self.fail_critic, self.good_rejudge,
                          triggered=True, audit_prompt=bad)]
        rep = self.score(rows)
        self.assertTrue(rep['audits']['failures'])
        self.assertEqual(rep['verdict'], 'NO_BENEFIT_SIGNAL')

    def test_candidate_sha_mismatch_fails_closed(self):
        rows = [_case_row(self.fz, 'n5-appetite', 'repaired', self.fail_critic, self.good_rejudge,
                          triggered=True, audit_prompt=clean_prompt(), bad_sha=True)]
        rep = self.score(rows)
        self.assertTrue(rep['candidate_integrity_problems'])
        self.assertEqual(rep['verdict'], 'NO_BENEFIT_SIGNAL')
        self.assertNotIn('after', rep['per_case'][0]['side_check'])

    def test_freeze_mismatch_raises(self):
        run = {'freeze_sha256': 'x', 'cases': []}
        with self.assertRaises(ValueError):
            sc.score_run(run, self.fz, self.fz_sha)

    def test_protocol_drift_raises(self):
        fz = n5.make_freeze()
        fz['protocol']['judge_sha256'] = '0' * 64
        run = {'freeze_sha256': n5.sha256_json(fz), 'cases': []}
        with self.assertRaises(ValueError):
            sc.score_run(run, fz, n5.sha256_json(fz))

    def test_source_sha_mismatch_raises(self):
        row = _case_row(self.fz, 'n5-iana', 'no_repair_needed', mk_report('uncertain'))
        row['source_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.score([row])

    def test_ci_reproducible_across_runs(self):
        rows = [_case_row(self.fz, 'n5-appetite', 'repaired', self.fail_critic, self.good_rejudge,
                          triggered=True, audit_prompt=clean_prompt())]
        a = self.score(rows)['metrics']['mean_total_score_delta_ci95']
        b = self.score(rows)['metrics']['mean_total_score_delta_ci95']
        self.assertEqual(a, b)


class CliTests(unittest.TestCase):
    def test_output_overwrite_refused(self):
        with TemporaryDirectory() as td:
            out = Path(td) / 'exists.json'
            out.write_text('{}', encoding='utf-8')
            rc = sc.main(['--run', str(Path(td) / 'run.json'), '--output', str(out),
                          '--freeze-path', str(Path(td) / 'fz.json')])
            self.assertEqual(rc, 3)


class FullPipelineCliTests(unittest.TestCase):
    def test_run_then_score_cli_zero_call(self):
        from unittest.mock import patch
        import tools.run_rubrics_judge as rrj
        freeze_path = n5.ROOT / n5.FREEZE_REL
        fail = mk_report('fail', mk_dims(cleanliness={'score': 2, 'severity': 'major'}))
        rejudge = mk_report('uncertain', mk_dims(cleanliness={'score': 3, 'severity': 'minor'}))
        clean = mk_report('uncertain')
        trace = mk_trace({'title': 'T', 'blocks': [{'kind': 'paragraph', 'text': 'hello'}]})
        with TemporaryDirectory() as td:
            run_path = Path(td) / 'run.json'
            score_path = Path(td) / 'score.json'
            with patch.object(n5, 'run_judge', side_effect=[fail, rejudge, clean]), \
                    patch.object(n5, 'run_agent', return_value=trace), \
                    patch.object(rrj, '_build_provider', return_value=object()):
                rc = n5.main(['--run', '--output', str(run_path), '--freeze-path', str(freeze_path),
                              '--max-cases', '2'])
            self.assertEqual(rc, 0)
            run = json.loads(run_path.read_text(encoding='utf-8'))
            self.assertEqual(run['budget']['used'], 3500)
            self.assertEqual([c['status'] for c in run['cases']], ['repaired', 'no_repair_needed'])
            rc = sc.main(['--run', str(run_path), '--output', str(score_path),
                          '--freeze-path', str(freeze_path)])
            self.assertEqual(rc, 0)
            rep = json.loads(score_path.read_text(encoding='utf-8'))
            self.assertEqual(rep['verdict'], 'REPAIR_BENEFIT_SIGNAL')
            self.assertEqual(rep['metrics']['paired_n'], 1)
            self.assertEqual(rep['metrics']['repair_trigger_rate'], 0.5)
            self.assertIn('side_check', rep['per_case'][0])
            self.assertIn('after', rep['per_case'][0]['side_check'])


if __name__ == '__main__':
    unittest.main()
