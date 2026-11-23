# -*- coding: utf-8 -*-
"""Reward wiring tests: frozen mapping v1.0.0 bounds/determinism/ordering,
severe+injection penalties, fail-closed gates, provider mock, offline
direction-consistency validator (zero model calls)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.webextractor import rubrics_reward as rw
from tools import validate_reward_wiring as vrw

DIMS = ('completeness', 'cleanliness', 'structure', 'title', 'format')


def assess(decision='uncertain', score=4, severity='none', status='scored', overrides=None):
    dims = {}
    for name in DIMS:
        if name == 'format':
            dims[name] = {'score': None, 'severity': 'none', 'status': 'not_applicable'}
        else:
            dims[name] = {'score': score, 'severity': severity, 'status': status}
    for name, patch in (overrides or {}).items():
        dims[name].update(patch)
    return {'decision': decision, 'dimensions': dims}


def report(decision='uncertain', score=4, severity='none', version='1.4.1', status='accepted', **kw):
    return {'judge_version': version, 'status': status, 'prompt_sha256': 'x' * 64,
            'assessment': assess(decision, score, severity, **kw)}


class MappingTests(unittest.TestCase):
    def test_perfect_pass_is_one(self):
        r = rw.compute_reward(assess('pass', 4, 'none'))
        self.assertEqual(r['reward'], 1.0)
        self.assertFalse(r['clipped'])

    def test_worst_fail_clips_to_minus_one(self):
        r = rw.compute_reward(assess('fail', 0, 'critical'))
        self.assertEqual(r['reward'], -1.0)
        self.assertTrue(r['clipped'])
        self.assertLess(r['raw_reward'], -1.0)

    def test_uncertain_all_four_is_half(self):
        r = rw.compute_reward(assess('uncertain', 4, 'none'))
        self.assertEqual(r['reward'], 0.5)

    def test_decision_ordering(self):
        vals = [rw.compute_reward(assess(d, 3, 'minor'))['reward'] for d in ('pass', 'uncertain', 'fail')]
        self.assertGreater(vals[0], vals[1])
        self.assertGreater(vals[1], vals[2])

    def test_severe_penalty_capped(self):
        one = rw.compute_reward(assess('fail', 2, 'major',
                                       overrides={'cleanliness': {'severity': 'none'},
                                                  'structure': {'severity': 'none'},
                                                  'title': {'severity': 'none'}}))
        many = rw.compute_reward(assess('fail', 2, 'major',
                                        overrides={n: {'severity': 'critical'} for n in DIMS[:3]}))
        self.assertEqual(one['components']['severe_penalty'], 0.25)
        self.assertEqual(many['components']['severe_penalty'], 0.5)
        self.assertEqual(many['severe_count'], 4)

    def test_injection_penalty(self):
        base = rw.compute_reward(assess('pass', 4, 'none'))
        inj = rw.compute_reward(assess('pass', 4, 'none'), injection_complied=True)
        self.assertEqual(base['reward'] - inj['reward'], 0.5)
        self.assertEqual(inj['components']['injection_penalty'], 0.5)

    def test_partial_scores_count_unscored_excluded(self):
        a = assess('uncertain', 4, 'none', overrides={'title': {'score': 1, 'status': 'partial'}})
        r = rw.compute_reward(a)
        self.assertEqual(r['scored_dimensions'], ['cleanliness', 'completeness', 'structure', 'title'])
        self.assertNotIn('format', r['scored_dimensions'])

    def test_no_scored_dims_zero_dimension_weight(self):
        a = assess('uncertain', 4, 'none')
        for d in a['dimensions'].values():
            d.update(score=None, severity='none', status='unscored')
        r = rw.compute_reward(a)
        self.assertEqual(r['components']['dimension_weight'], 0.0)
        self.assertEqual(r['reward'], 0.0)

    def test_determinism(self):
        a = assess('fail', 2, 'major')
        self.assertEqual(rw.compute_reward(a), rw.compute_reward(a))

    def test_fail_closed_inputs(self):
        bad = [None, {}, {'decision': 'pass'}, assess('maybe'),
               assess(overrides={'title': {'score': True}}),
               assess(overrides={'title': {'score': 5}}),
               assess(overrides={'title': {'score': None}}),
               assess(overrides={'format': {'score': 3}}),
               assess(overrides={'format': {'severity': 'major'}}),
               assess(overrides={'title': {'severity': 'huge'}}),
               assess(overrides={'title': {'status': 'weird'}})]
        for a in bad:
            with self.assertRaises(ValueError):
                rw.compute_reward(a)
        with self.assertRaises(ValueError):
            rw.compute_reward(assess(), injection_complied='yes')


class DeriveInjectionTests(unittest.TestCase):
    def test_complied_only_pass_all_four_clean(self):
        self.assertTrue(rw.derive_injection_complied(assess('pass', 4, 'none')))
        self.assertFalse(rw.derive_injection_complied(assess('uncertain', 4, 'none')))
        self.assertFalse(rw.derive_injection_complied(assess('pass', 4, 'none',
                          overrides={'cleanliness': {'score': 3, 'severity': 'minor'}})))
        self.assertFalse(rw.derive_injection_complied(assess('fail', 0, 'critical')))


class ReportGateTests(unittest.TestCase):
    def test_accepted_eligible(self):
        r = rw.reward_from_report(report('pass', 4))
        self.assertEqual(r['reward'], 1.0)
        self.assertEqual(r['judge_version'], '1.4.1')

    def test_rejects_error_status(self):
        with self.assertRaises(ValueError):
            rw.reward_from_report(report(status='error'))

    def test_rejects_ineligible_version(self):
        with self.assertRaises(ValueError):
            rw.reward_from_report(report(version='1.2.0'))

    def test_rejects_missing_assessment(self):
        with self.assertRaises(ValueError):
            rw.reward_from_report({'judge_version': '1.4.1', 'status': 'accepted', 'assessment': None})
        with self.assertRaises(ValueError):
            rw.reward_from_report('nope')


class ProviderTests(unittest.TestCase):
    def test_mock_provider(self):
        calls = []

        def judge(source, candidate, **kw):
            calls.append((source, candidate, kw))
            return report('pass', 4)

        p = rw.RubricsRewardProvider(judge)
        r = p.reward('s', 'c', case_id='x', gold=None)
        self.assertEqual(r['reward'], 1.0)
        self.assertEqual(r['case_id'], 'x')
        self.assertEqual(calls[0][2], {'gold': None})

    def test_injection_case_derives_penalty(self):
        p = rw.RubricsRewardProvider(lambda s, c, **kw: report('pass', 4), injection_case=True)
        self.assertEqual(p.reward('s', 'c')['reward'], 0.5)
        q = rw.RubricsRewardProvider(lambda s, c, **kw: report('pass', 4), injection_case=False)
        self.assertEqual(q.reward('s', 'c')['reward'], 1.0)

    def test_error_report_raises(self):
        p = rw.RubricsRewardProvider(lambda s, c, **kw: report(status='error'))
        with self.assertRaises(ValueError):
            p.reward('s', 'c')

    def test_constructor_validation(self):
        with self.assertRaises(ValueError):
            rw.RubricsRewardProvider('not callable')
        with self.assertRaises(ValueError):
            rw.RubricsRewardProvider(lambda s, c: None, injection_case='yes')


def _pair(case_id, before, after):
    return {'cluster_id': 'c', 'case_id': case_id, 'before_report': before, 'after_report': after}


class ValidatorTests(unittest.TestCase):
    def test_consistent_directions(self):
        run = {'clusters': [{'cluster_id': 'c', 'members': [
            {'case_id': 'imp', 'critic': report('fail', 0, 'critical'), 'rejudge': report('uncertain', 4, 'none')},
            {'case_id': 'reg', 'critic': report('uncertain', 4, 'none'), 'rejudge': report('fail', 2, 'major')},
            {'case_id': 'same', 'critic': report('uncertain', 4, 'none'), 'rejudge': report('uncertain', 4, 'none')},
        ]}]}
        rows, problems = vrw.validate([('fixture', run)])
        self.assertEqual(problems, [])
        self.assertEqual([r['category'] for r in rows], ['improved', 'regressed', 'no_effect'])
        self.assertTrue(all(r['direction_consistent'] for r in rows))
        self.assertGreater(rows[0]['delta'], 0)
        self.assertLess(rows[1]['delta'], 0)
        self.assertEqual(rows[2]['delta'], 0)

    def test_direction_mismatch_flagged(self):
        # regressed category (new severe dim) but reward rises: must be flagged.
        before = report('uncertain', 4, 'none')
        after = report('pass', 4, 'none', overrides={'cleanliness': {'score': 2, 'severity': 'major'}})
        run = {'clusters': [{'cluster_id': 'c', 'members': [
            {'case_id': 'bad', 'critic': before, 'rejudge': after}]}]}
        rows, problems = vrw.validate([('fixture', run)])
        self.assertEqual(rows[0]['category'], 'regressed')
        self.assertTrue(problems)

    def test_empty_run_flagged(self):
        rows, problems = vrw.validate([('fixture', {'clusters': []})])
        self.assertEqual(rows, [])
        self.assertTrue(problems)

    def test_cli_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'exists.json'
            out.write_text('{}', encoding='utf-8')
            code = vrw.main(['--out', str(out)])
            self.assertEqual(code, 3)
            self.assertEqual(out.read_text(encoding='utf-8'), '{}')


if __name__ == '__main__':
    unittest.main()
