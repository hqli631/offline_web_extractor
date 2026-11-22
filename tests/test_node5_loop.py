# -*- coding: utf-8 -*-
"""Node 5 loop tests: adapter, leakage audit, wrapper, budget guard, freeze,
orchestration (mocked judge/agent), and one real-executor smoke. Zero model calls."""
import unittest
from unittest.mock import patch

from src.webextractor.extractor import extract_html
from src.webextractor.rule_agent import run_agent
import tools.node5_loop as n5

DIMS = ('completeness', 'cleanliness', 'structure', 'title', 'format')


def mk_dims(**overrides):
    dims = {name: {'score': 4, 'status': 'scored', 'severity': 'none', 'reason': 'ok', 'evidence': []}
            for name in DIMS}
    for name, upd in overrides.items():
        dims[name].update(upd)
    return dims


def mk_report(decision='uncertain', dims=None, status='accepted', mode='source_only', tokens=1000):
    return {'status': status, 'mode': mode,
            'assessment': {'decision': decision, 'dimensions': dims if dims is not None else mk_dims()},
            'usage': {'input_tokens': tokens - 100, 'output_tokens': 100, 'total_tokens': tokens}}


def mk_trace(accepted=True, result=None, tokens=500):
    if result is None:
        result = {'title': 'T', 'blocks': [{'kind': 'paragraph', 'text': 'hello'}]}
    rule = {'version': 1, 'container_xpath': '//article', 'exclude_xpaths': []}
    return {'status': 'runtime_accepted' if accepted else 'attempts_exhausted',
            'runtime_accepted': accepted, 'selected_rule': rule if accepted else None,
            'attempts': [{'number': 1,
                          'prompt': {'instruction': 'x', 'reference_pages': [], 'previous_attempts': []},
                          'usage': {'input_tokens': tokens - 50, 'output_tokens': 50, 'total_tokens': tokens},
                          'executions': [{'id': 'n5-appetite',
                                          'execution': {'status': 'ok', 'result': result}}]}]}


class AdapterTests(unittest.TestCase):
    def test_feedback_refuses_with_gold(self):
        with self.assertRaises(ValueError):
            n5.critic_feedback(mk_report(mode='with_gold'))

    def test_feedback_refuses_rejected(self):
        with self.assertRaises(ValueError):
            n5.critic_feedback(mk_report(status='error'))

    def test_feedback_extracts_defects_and_caps_evidence(self):
        ev = [{'ref': 's:%d' % i, 'quote': 'q%d' % i} for i in range(6)]
        dims = mk_dims(cleanliness={'score': 2, 'severity': 'major', 'evidence': ev},
                       structure={'score': 3, 'severity': 'minor'})
        fb = n5.critic_feedback(mk_report('fail', dims=dims))
        self.assertEqual(fb['decision'], 'fail')
        self.assertEqual({d['dimension'] for d in fb['defects']}, {'cleanliness', 'structure'})
        clean = next(d for d in fb['defects'] if d['dimension'] == 'cleanliness')
        self.assertEqual(len(clean['evidence']), 4)
        self.assertIn('untrusted', fb['guidance'])

    def test_feedback_clean_has_no_defects(self):
        fb = n5.critic_feedback(mk_report('uncertain'))
        self.assertEqual(fb['defects'], [])


class AuditTests(unittest.TestCase):
    def prompt(self, **extra):
        p = {'instruction': 'x', 'reference_pages': [{'id': 'c', 'source': '<html></html>'}],
             'previous_attempts': [], 'critic_feedback': {'decision': 'fail', 'defects': [], 'guidance': 'adjust'},
             'baseline_extraction_preview': {'title': 't', 'block_count': 1, 'body_preview': 'b'}}
        p.update(extra)
        return p

    def test_audit_clean_passes(self):
        res = n5.audit_repair_prompt(self.prompt(), mk_report())
        self.assertTrue(res['passed'], res['problems'])
        self.assertEqual(res['prompt_sha256'], n5.sha256_json(self.prompt()))

    def test_audit_forbidden_nested_key_fails(self):
        p = self.prompt()
        p['reference_pages'][0]['gold_blocks'] = []
        res = n5.audit_repair_prompt(p, mk_report())
        self.assertFalse(res['passed'])
        self.assertTrue(any('forbidden' in pr for pr in res['problems']))

    def test_audit_unexpected_key_fails(self):
        res = n5.audit_repair_prompt(self.prompt(expected_json={}), mk_report())
        self.assertFalse(res['passed'])

    def test_audit_non_source_only_critic_fails(self):
        res = n5.audit_repair_prompt(self.prompt(), mk_report(mode='with_gold'))
        self.assertFalse(res['passed'])

    def test_audit_gold_mention_in_feedback_fails(self):
        p = self.prompt(critic_feedback={'guidance': 'compare against the gold blocks'})
        res = n5.audit_repair_prompt(p, mk_report())
        self.assertFalse(res['passed'])


class _Inner:
    model = 'fake'

    def __init__(self):
        self.seen = []

    def generate(self, prompt, *, timeout_seconds, max_output_tokens):
        self.seen.append(prompt)
        return {'content': '{}', 'usage': {'input_tokens': 1, 'output_tokens': 1, 'total_tokens': 2}}


class WrapperTests(unittest.TestCase):
    def test_wrapper_injects_and_logs(self):
        inner = _Inner()
        log = []
        fb = {'decision': 'fail', 'defects': [{'dimension': 'cleanliness'}], 'guidance': 'g'}
        preview = {'title': 't', 'block_count': 2, 'body_preview': 'body'}
        wrapped = n5.CriticGuidedProvider(inner, fb, preview, log)
        base = {'instruction': 'x', 'reference_pages': [], 'previous_attempts': []}
        wrapped.generate(base, timeout_seconds=5, max_output_tokens=64)
        self.assertEqual(len(inner.seen), 1)
        self.assertEqual(inner.seen[0]['critic_feedback'], fb)
        self.assertEqual(inner.seen[0]['baseline_extraction_preview'], preview)
        self.assertNotIn('critic_feedback', base)
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]['prompt_sha256'], n5.sha256_json(inner.seen[0]))
        self.assertTrue(n5.audit_repair_prompt(log[0]['prompt'], mk_report())['passed'])


class BudgetTests(unittest.TestCase):
    def test_guard_reserve_and_skip(self):
        g = n5.BudgetGuard(20000)
        self.assertTrue(g.allow('judge', 'c'))
        g.record({'total_tokens': 5000})
        self.assertFalse(g.allow('judge', 'c'))
        self.assertTrue(g.allow('rule', 'c'))
        self.assertEqual(g.used, 5000)
        self.assertEqual(g.skipped, [{'case_id': 'c', 'kind': 'judge', 'used': 5000}])

    def test_guard_ignores_bad_usage(self):
        g = n5.BudgetGuard(20000)
        g.record(None)
        g.record({'total_tokens': 'x'})
        g.record({})
        self.assertEqual(g.used, 0)


class FreezeTests(unittest.TestCase):
    def test_freeze_structure_and_clean_check(self):
        fz = n5.make_freeze()
        self.assertEqual(n5.check_freeze(fz), [])
        self.assertEqual(len(fz['cases']), 6)
        self.assertEqual(fz['protocol']['judge_sha256'],
                         n5.sha256_bytes((n5.ROOT / 'src/webextractor/rubrics_judge.py').read_bytes()))
        self.assertEqual(fz['protocol']['model'], 'qwen3.8-27b')
        self.assertEqual(fz['budget']['token_cap'], 220000)
        self.assertEqual(fz['budget']['refined_worst_case_calls'], 25)
        self.assertIn('trigger_rule', fz)
        self.assertEqual(fz['seed'], 20261119)
        self.assertEqual(fz['B'], 10000)

    def test_freeze_drift_detected(self):
        fz = n5.make_freeze()
        fz['protocol']['judge_sha256'] = '0' * 64
        self.assertTrue(any('judge sha' in p for p in n5.check_freeze(fz)))
        fz = n5.make_freeze()
        fz['cases'][0]['source_sha256'] = '0' * 64
        self.assertTrue(any('source drift' in p for p in n5.check_freeze(fz)))
        fz = n5.make_freeze()
        fz['freeze_version'] = 'other'
        self.assertTrue(n5.check_freeze(fz))


class RunCaseTests(unittest.TestCase):
    def setUp(self):
        self.case = n5.CASES[0]
        self.freeze = n5.make_freeze()
        self.guard = n5.BudgetGuard(220000)

    def run_case(self, judge_reports, trace=None):
        with patch.object(n5, 'run_judge', side_effect=judge_reports) as rj, \
                patch.object(n5, 'run_agent', return_value=trace) as ra:
            row = n5.run_case(self.case, object(), object(), self.guard, self.freeze)
        return row, rj, ra

    def test_no_repair_on_zero_defect_uncertain(self):
        row, rj, ra = self.run_case([mk_report('uncertain')])
        self.assertEqual(row['status'], 'no_repair_needed')
        self.assertFalse(row['repair']['triggered'])
        self.assertEqual(row['baseline_defect_count'], 0)
        ra.assert_not_called()
        self.assertEqual(len(row['calls']), 1)
        self.assertIsNone(rj.call_args_list[0].kwargs['gold'])

    def test_repair_path_full(self):
        fail = mk_report('fail', dims=mk_dims(cleanliness={'score': 2, 'severity': 'major'}))
        rejudge = mk_report('uncertain', dims=mk_dims(cleanliness={'score': 3, 'severity': 'minor'}))
        row, rj, ra = self.run_case([fail, rejudge], trace=mk_trace())
        self.assertEqual(row['status'], 'repaired')
        self.assertTrue(row['repair']['triggered'])
        self.assertIn('defects=1', row['repair']['trigger_reason'])
        self.assertEqual(self.guard.used, 2500)
        self.assertEqual([c['kind'] for c in row['calls']], ['critic', 'rule_generation', 'rejudge'])
        self.assertEqual(rj.call_count, 2)
        for call in rj.call_args_list:
            self.assertIsNone(call.kwargs['gold'])
        base = extract_html((n5.ROOT / self.case['source']).read_bytes())
        self.assertEqual(rj.call_args_list[0].args[1], {'title': base.title, 'blocks': base.to_dict()['blocks']})
        self.assertEqual(rj.call_args_list[1].args[1], {'title': 'T', 'blocks': [{'kind': 'paragraph', 'text': 'hello'}]})
        self.assertEqual(row['repaired_candidate_sha256'],
                         n5.sha256_json({'title': 'T', 'blocks': [{'kind': 'paragraph', 'text': 'hello'}]}))

    def test_critic_rejected(self):
        row, rj, ra = self.run_case([mk_report(status='error')])
        self.assertEqual(row['status'], 'critic_rejected')
        ra.assert_not_called()

    def test_repair_failed(self):
        fail = mk_report('fail', dims=mk_dims(cleanliness={'score': 2, 'severity': 'major'}))
        row, rj, ra = self.run_case([fail], trace=mk_trace(accepted=False))
        self.assertEqual(row['status'], 'repair_failed')
        self.assertEqual(rj.call_count, 1)

    def test_rejudge_rejected(self):
        fail = mk_report('fail', dims=mk_dims(cleanliness={'score': 2, 'severity': 'major'}))
        row, rj, ra = self.run_case([fail, mk_report(status='error')], trace=mk_trace())
        self.assertEqual(row['status'], 'rejudge_rejected')

    def test_budget_skip_before_critic(self):
        guard = n5.BudgetGuard(100)
        with patch.object(n5, 'run_judge') as rj, patch.object(n5, 'run_agent') as ra:
            row = n5.run_case(self.case, object(), object(), guard, self.freeze)
        self.assertEqual(row['status'], 'skipped_budget')
        rj.assert_not_called()
        ra.assert_not_called()

    def test_budget_skip_before_rule(self):
        guard = n5.BudgetGuard(20000)
        fail = mk_report('fail', dims=mk_dims(cleanliness={'score': 2, 'severity': 'major'}), tokens=13000)
        with patch.object(n5, 'run_judge', side_effect=[fail]) as rj, patch.object(n5, 'run_agent') as ra:
            row = n5.run_case(self.case, object(), object(), guard, self.freeze)
        self.assertEqual(row['status'], 'skipped_budget')
        self.assertTrue(row['repair']['triggered'])
        ra.assert_not_called()
        self.assertEqual(guard.used, 13000)


class RealExecutorSmokeTests(unittest.TestCase):
    def test_critic_guided_rule_runs_on_real_executor(self):
        html = b'<html><head><title>T</title></head><body><article><p>alpha beta</p><p>gamma</p></article><nav>noise</nav></body></html>'
        rule = {'version': 1, 'container_xpath': '//article', 'exclude_xpaths': []}

        class Scripted:
            name = 'scripted'
            model = 'fake'

            def generate(self, prompt, *, timeout_seconds, max_output_tokens):
                import json as _json
                return {'content': _json.dumps(rule), 'usage': {'input_tokens': 10, 'output_tokens': 10, 'total_tokens': 20},
                        'finish_reason': 'stop'}

        log = []
        fb = {'decision': 'fail', 'defects': [{'dimension': 'cleanliness', 'score': 2, 'severity': 'major',
                                              'reason': 'nav noise', 'evidence': [{'ref': 's:1', 'quote': 'noise'}]}],
              'guidance': 'remove noise'}
        wrapped = n5.CriticGuidedProvider(Scripted(), fb, {'title': 'T', 'block_count': 3, 'body_preview': 'alpha'}, log)
        trace = run_agent([{'id': 'smoke', 'source': html}], wrapped, max_attempts=2,
                          execution_timeout=10.0, total_timeout=60.0, max_output_tokens=256, evidence_chars=4000)
        self.assertEqual(trace['status'], 'runtime_accepted', trace)
        self.assertEqual(len(log), 1)
        self.assertEqual(set(log[0]['prompt']), n5.ALLOWED_PROMPT_KEYS)
        self.assertTrue(n5.audit_repair_prompt(log[0]['prompt'], mk_report())['passed'])
        result = trace['attempts'][-1]['executions'][0]['execution']['result']
        self.assertTrue(result['blocks'])
        self.assertNotIn('noise', ' '.join(b['text'] for b in result['blocks']))


if __name__ == '__main__':
    unittest.main()
