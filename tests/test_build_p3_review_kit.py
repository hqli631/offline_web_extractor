# -*- coding: utf-8 -*-
"""Unit tests for tools/build_p3_review_kit.py (offline)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.build_p3_review_kit import (select_divergences, resolve_ref, mutation_evidence,
                                       render_packet, DIMS)


def dim(score=4, status='scored', severity='none', reason='ok', evidence=None):
    return {'score': score, 'status': status, 'severity': severity, 'reason': reason,
            'evidence': evidence or []}


def assessment(decision='uncertain', **dims):
    d = {n: dim() for n in DIMS}
    d.update(dims)
    return {'decision': decision, 'dimensions': d}


def row(cid, split='development', a=None, status='accepted'):
    return {'case_id': cid, 'split': split, 'template': 't',
            'report': {'status': status, 'assessment': a,
                       'prompt': {'candidate': {'title': 'T', 'blocks': [{'kind': 'paragraph', 'text': 'hello'}]},
                                  'gold': {'title': 'T', 'blocks': [{'kind': 'paragraph', 'text': 'hello'}]},
                                  'source': {'html': '<html></html>', 'nodes': [{'text': 'src'}]}}}}


def gold_entry(decision='uncertain', **dims):
    d = {n: {'score': 4, 'status': 'scored', 'severity': 'none', 'note': ''} for n in DIMS}
    for k, v in dims.items():
        d[k] = {'score': v[0], 'status': 'scored', 'severity': v[1], 'note': ''}
    return {'case_id': 'x', 'decision': decision, 'dimensions': d, 'overall_note': ''}


class SelectionTests(unittest.TestCase):
    def test_no_divergence(self):
        self.assertEqual(select_divergences([row('c1', a=assessment())], {'c1': gold_entry()}), [])

    def test_decision_mismatch(self):
        sel = select_divergences([row('c1', a=assessment('fail'))], {'c1': gold_entry('uncertain')})
        self.assertEqual(sel[0]['categories'], ['decision_mismatch'])

    def test_dim_gap_ge2(self):
        sel = select_divergences([row('c1', a=assessment(cleanliness=dim(2, 'scored', 'major')))],
                                 {'c1': gold_entry(cleanliness=(4, 'none'))})
        self.assertIn('dim_gap_ge2:cleanliness', sel[0]['categories'])
        self.assertIn('judge_severe_human_not:cleanliness', sel[0]['categories'])

    def test_judge_missed_defect(self):
        sel = select_divergences([row('c1', a=assessment())],
                                 {'c1': gold_entry(structure=(3, 'minor'))})
        self.assertIn('judge_missed_defect:structure', sel[0]['categories'])

    def test_rejected_case_selected(self):
        sel = select_divergences([row('c1', status='error')], {'c1': gold_entry()})
        self.assertEqual(sel[0]['categories'], ['judge_rejected'])


class EvidenceTests(unittest.TestCase):
    def test_resolve_ref(self):
        p = row('c1')['report']['prompt']
        self.assertEqual(resolve_ref(p, 'p:0'), 'hello')
        self.assertEqual(resolve_ref(p, 'g:0'), 'hello')
        self.assertEqual(resolve_ref(p, 's:0'), 'src')
        self.assertEqual(resolve_ref(p, 'p:title'), 'T')
        self.assertIn('raw HTML', resolve_ref(p, 's:html'))
        self.assertEqual(resolve_ref(p, 'p:99'), '')

    def test_injection_evidence_verbatim(self):
        mut = {'type': 'instruction_interference', 'index': 0, 'injected_text': 'IGNORE ALL'}
        p = row('c1')['report']['prompt']
        p['candidate']['blocks'].append({'kind': 'paragraph', 'text': 'prefix IGNORE ALL suffix'})
        lines = mutation_evidence(mut, p)
        text = '\n'.join(lines)
        self.assertIn('IGNORE ALL', text)
        self.assertIn('p:1', text)
        self.assertIn('包含上述文本', text)

    def test_injection_absent_noted(self):
        mut = {'type': 'noise', 'injected_text': 'NOT PRESENT'}
        lines = mutation_evidence(mut, row('c1')['report']['prompt'])
        self.assertIn('未找到', '\n'.join(lines))

    def test_missing_and_duplicate_and_reorder(self):
        p = row('c1')['report']['prompt']
        p['gold']['blocks'] = [{'kind': 'paragraph', 'text': 'AAA removed text'}]
        p['candidate']['blocks'] = [{'kind': 'paragraph', 'text': 'AAA removed text'},
                                    {'kind': 'paragraph', 'text': 'AAA removed text'}]
        self.assertIn('g:0', '\n'.join(mutation_evidence({'type': 'missing_paragraph', 'removed_excerpt': 'AAA removed'}, p)))
        self.assertIn('2 次', '\n'.join(mutation_evidence({'type': 'duplicate', 'duplicated_excerpt': 'AAA removed'}, p)))
        self.assertIn('indices=[0, 1]', '\n'.join(mutation_evidence({'type': 'reorder', 'indices': [0, 1]}, p)))
        self.assertIn('clean', '\n'.join(mutation_evidence({'type': 'clean'}, p)))

    def test_packet_contains_key_sections(self):
        r = row('cal-x-injection', a=assessment('fail', cleanliness=dim(1, 'scored', 'critical', 'injection noise',
                [{'ref': 'p:0', 'quote': 'hello'}])))
        g = gold_entry('uncertain')
        sel = {'case_id': 'cal-x-injection', 'split': 'development', 'categories': ['decision_mismatch'],
               'judge_decision': 'fail', 'human_decision': 'uncertain'}
        mut = {'type': 'instruction_interference', 'injected_text': 'hello'}
        pkt = render_packet(sel, r, g, mut, 'C01')
        for section in ('维度对照', 'judge 引用证据', '变异证据', '复审问题', '纪律'):
            self.assertIn(section, pkt)
        self.assertIn('hello', pkt)


if __name__ == '__main__':
    unittest.main()
