"""P1 judge v1.1.0 + tooling targeted tests (zero model calls)."""
import json
import tempfile
import unittest
from pathlib import Path

from src.webextractor.rubrics_judge import (build_prompt, validate_assessment, run_judge,
                                            JUDGE_VERSION, _ws_fold, PHRASING_VARIANTS, MENU_QUOTE_CHARS)
from src.webextractor.rubrics_v2 import DIMENSIONS
from tools.run_rubrics_judge import config_signature, run_case, run_batch, cache_key, sha256_bytes
import tools.run_p1_probes as PP
import tools.score_p1_results as SP
import tools.amend_freeze_v3 as AF
from tools.ingest_human_labels import compare_human_case, aggregate_human

ROOT = Path(__file__).resolve().parents[1]
NBSP = chr(160)
NL = chr(10)
SOURCE = ('<html><head><meta charset="utf-8"></head><body><main><h1>1.  Title</h1><p>Hello article</p>'
          '<ul><li>Item one</li></ul><pre>code  here</pre></main>'
          '<nav><p>Menu advertisement</p></nav></body></html>')
DOC = {'title': '1. Title', 'blocks': [{'kind': 'paragraph', 'text': 'Hello article'}]}


def assessment(ref='s:0', quote='1. Title'):
    return {'schema_version': 1, 'dimensions': {n: {'score': 4, 'status': 'scored', 'severity': 'none',
            'reason': 'ok', 'evidence': [{'ref': ref, 'quote': quote}]} for n in DIMENSIONS}}


class Provider:
    name = 'mock-judge'
    model = 'qwen3.8-27b'
    def __init__(self, value=None, finish='stop'):
        self.value = value or assessment(); self.finish = finish; self.calls = 0
    def generate(self, prompt, **kwargs):
        self.calls += 1; self.prompt = prompt
        return {'content': json.loads(json.dumps(self.value)), 'model': self.model, 'finish_reason': self.finish,
                'usage': {'input_tokens': 10, 'output_tokens': 20, 'total_tokens': 30}}


def mkrow(cid, split, decision, sev, score, status='accepted', mode='with_gold'):
    if status == 'accepted':
        dims = {d: {'score': score, 'status': 'scored', 'severity': sev, 'reason': 'r',
                    'evidence': [{'ref': 's:0', 'quote': 'q'}]} for d in DIMENSIONS}
        report = {'status': 'accepted', 'assessment': {'decision': decision, 'dimensions': dims},
                  'usage': None, 'elapsed_seconds': 1.0}
    else:
        report = {'status': 'error', 'assessment': None,
                  'error': {'type': 'ValueError', 'stage': 'validation', 'detail': 'Scoring needs source/reference evidence'}}
    return {'case_id': cid, 'split': split, 'template': 't', 'case_meta': {'mode': mode},
            'report': report, 'cache_hit': False}


def mkgold(cid, decision, sev, score):
    return {'case_id': cid, 'decision': decision,
            'dimensions': {d: {'score': score, 'status': 'scored', 'severity': sev} for d in DIMENSIONS}}


class JudgeV11Tests(unittest.TestCase):
    def test_version_bumped(self):
        self.assertEqual(JUDGE_VERSION, '1.2.0')

    def test_menus_present_and_deterministic(self):
        p1, reg, _ = build_prompt(SOURCE, DOC, DOC)
        p2, _, _ = build_prompt(SOURCE, DOC, DOC)
        self.assertEqual(p1, p2)
        self.assertIn('evidence_menus', p1)
        self.assertEqual(set(p1['evidence_menus']), set(DIMENSIONS))

    def test_menu_refs_in_registry_and_items_validate(self):
        p, reg, _ = build_prompt(SOURCE, DOC, DOC)
        for name, items in p['evidence_menus'].items():
            for it in items:
                self.assertIn(it['ref'], reg)
                self.assertTrue(_ws_fold(it['quote']) in _ws_fold(reg[it['ref']]))
                self.assertLessEqual(len(it['quote']), MENU_QUOTE_CHARS)

    def test_menu_caps(self):
        p, _, _ = build_prompt(SOURCE, DOC, DOC)
        m = p['evidence_menus']
        self.assertLessEqual(len(m['cleanliness']), 20)
        self.assertLessEqual(len(m['structure']), 26)
        self.assertLessEqual(len(m['title']), 4)
        self.assertLessEqual(len(m['format']), 8)
        self.assertLessEqual(len(m['completeness']), 10)

    def test_cleanliness_menu_has_source_or_gold(self):
        p, _, _ = build_prompt(SOURCE, DOC, DOC)
        self.assertTrue(any(it['ref'].startswith(('s:', 'g:')) for it in p['evidence_menus']['cleanliness']))

    def test_menu_item_usable_as_evidence(self):
        p, reg, _ = build_prompt(SOURCE, DOC, DOC)
        val = assessment(ref='s:0', quote='1. Title')
        item = p['evidence_menus']['cleanliness'][0]
        self.assertTrue(item['ref'].startswith(('s:', 'g:')))
        val['dimensions']['cleanliness']['evidence'] = [item]
        validate_assessment(val, reg)

    def test_budget_aware_trimming(self):
        full, _, _ = build_prompt(SOURCE, DOC, DOC, max_prompt_chars=100000)
        base = {k: v for k, v in full.items() if k != 'evidence_menus'}
        base_size = len(json.dumps(base, ensure_ascii=False))
        tight, _, meta = build_prompt(SOURCE, DOC, DOC, max_prompt_chars=base_size + 60)
        self.assertLessEqual(meta['prompt_chars'], base_size + 60)
        maxlen = max((len(it['quote']) for v in tight['evidence_menus'].values() for it in v), default=0)
        self.assertLess(maxlen, MENU_QUOTE_CHARS)
        with self.assertRaises(ValueError):
            build_prompt(SOURCE, DOC, DOC, max_prompt_chars=base_size - 1)

    def test_ws_fold_double_space_accepted(self):
        _, reg, _ = build_prompt(SOURCE, DOC)
        validate_assessment(assessment(ref='s:0', quote='1. Title'), reg)

    def test_ws_fold_newline_accepted(self):
        src = '<html><body><p>Hello' + NL + 'world</p></body></html>'
        doc = {'title': 't', 'blocks': [{'kind': 'paragraph', 'text': 'x'}]}
        _, reg, _ = build_prompt(src, doc)
        ref = [r for r in reg if r.startswith('s:') and 'Hello' in reg[r]][0]
        val = assessment(ref=ref, quote='Hello world')
        validate_assessment(val, reg)

    def test_ws_fold_nbsp_accepted(self):
        src = '<html><head><meta charset="utf-8"></head><body><h1>Domain' + NBSP + 'Names</h1></body></html>'
        doc = {'title': 'Domain Names', 'blocks': [{'kind': 'paragraph', 'text': 'x'}]}
        _, reg, _ = build_prompt(src, doc)
        validate_assessment(assessment(ref='s:0', quote='Domain Names'), reg)

    def test_paraphrase_rejected(self):
        _, reg, _ = build_prompt(SOURCE, DOC)
        with self.assertRaises(ValueError):
            validate_assessment(assessment(ref='s:0', quote='totally invented text'), reg)

    def test_whitespace_only_rejected(self):
        _, reg, _ = build_prompt(SOURCE, DOC)
        for q in ('   ', NBSP, ' ' + NBSP + ' '):
            with self.assertRaises(ValueError):
                validate_assessment(assessment(ref='s:0', quote=q), reg)

    def test_suffix_extra_rejected(self):
        _, reg, _ = build_prompt(SOURCE, DOC)
        with self.assertRaises(ValueError):
            validate_assessment(assessment(ref='s:0', quote='1. Title Extra'), reg)

    def test_perturbation_default_identical(self):
        a, _, _ = build_prompt(SOURCE, DOC, DOC)
        b, _, _ = build_prompt(SOURCE, DOC, DOC, source_order_seed=None, dimension_phrasing=None)
        self.assertEqual(a, b)

    def test_seed_shuffle_registry_intact(self):
        a, rega, _ = build_prompt(SOURCE, DOC, DOC)
        b, regb, _ = build_prompt(SOURCE, DOC, DOC, source_order_seed=42)
        self.assertEqual(rega, regb)
        self.assertNotEqual([n['ref'] for n in a['source']['nodes']], [n['ref'] for n in b['source']['nodes']])
        self.assertEqual({n['ref'] for n in a['source']['nodes']}, {n['ref'] for n in b['source']['nodes']})

    def test_phrasing_variant_keeps_rules(self):
        a, _, _ = build_prompt(SOURCE, DOC, DOC)
        b, _, _ = build_prompt(SOURCE, DOC, DOC, dimension_phrasing='neutral_v1')
        self.assertNotEqual(a['protocol']['dimensions']['cleanliness'], b['protocol']['dimensions']['cleanliness'])
        self.assertIn('never only p:N', b['protocol']['dimensions']['cleanliness'])
        self.assertIn('never only p:N', b['protocol']['dimensions']['structure'])

    def test_invalid_perturbation_rejected(self):
        for seed in ('x', True, 1.5):
            with self.assertRaises(ValueError):
                build_prompt(SOURCE, DOC, source_order_seed=seed)
        with self.assertRaises(ValueError):
            build_prompt(SOURCE, DOC, dimension_phrasing='bogus')

    def test_run_judge_records_probe_settings(self):
        rep = run_judge(SOURCE, DOC, Provider(), gold=DOC, source_order_seed=5)
        self.assertEqual(rep['status'], 'accepted')
        self.assertEqual(rep['settings']['source_order_seed'], 5)
        self.assertIsNone(rep['settings']['dimension_phrasing'])

    def test_run_judge_production_accepted(self):
        rep = run_judge(SOURCE, DOC, Provider(), gold=DOC)
        self.assertEqual(rep['status'], 'accepted')
        self.assertEqual(rep['judge_version'], '1.2.0')


class RunnerP1Tests(unittest.TestCase):
    def test_signature_keys_unchanged(self):
        sig = config_signature('qwen3.8-27b', 2200, 20000, 90.0)
        self.assertEqual(set(sig), {'model', 'max_output_tokens', 'max_source_chars', 'timeout_seconds', 'judge_version', 'rubrics_version'})
        self.assertEqual(sig['judge_version'], '1.2.0')

    def _manifest(self, tmp, cases):
        (tmp / 'page.html').write_text(SOURCE, encoding='utf-8')
        man = {'judge_manifest_version': 1, 'cases': cases}
        mp = tmp / 'manifest.json'
        mp.write_text(json.dumps(man), encoding='utf-8')
        return mp

    def _case(self, cid, split):
        return {'case_id': cid, 'template': 't', 'split': split, 'source': 'page.html', 'candidate': 'extract'}

    def test_split_filter_dev_only(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            mp = self._manifest(tmp, [self._case('c1', 'development'), self._case('c2', 'frozen_test')])
            rep = run_batch(mp, Provider(), model='qwen3.8-27b', max_calls=10, split_filter='development',
                            cache_path=tmp / 'cache.json', report_path=tmp / 'report.json')
            self.assertEqual(rep['split_filter'], 'development')
            self.assertEqual([r['case_id'] for r in rep['cases']], ['c1'])
            self.assertEqual(rep['manifest_sha256'], sha256_bytes(mp.read_bytes()))

    def test_split_filter_empty_raises(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            mp = self._manifest(tmp, [self._case('c1', 'development')])
            with self.assertRaises(ValueError):
                run_batch(mp, Provider(), split_filter='smoke', cache_path=tmp / 'c.json')

    def test_split_filter_invalid_raises(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            mp = self._manifest(tmp, [self._case('c1', 'development')])
            with self.assertRaises(ValueError):
                run_batch(mp, Provider(), split_filter='bogus', cache_path=tmp / 'c.json')

    def test_probe_cache_separation(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            mp = self._manifest(tmp, [self._case('c1', 'development')])
            man = json.loads(mp.read_text(encoding='utf-8'))
            case = man['cases'][0]
            sig = config_signature('qwen3.8-27b', 2200, 40000, 90.0)
            cache = {}
            k0, _, _, _ = run_case(case, tmp, Provider(), sig, cache, False, allow_call=False, probe=None)
            k1, _, _, _ = run_case(case, tmp, Provider(), sig, cache, False, allow_call=False, probe={'source_order_seed': 1})
            self.assertNotEqual(k0, k1)


class AmendmentP1Tests(unittest.TestCase):
    def test_label_without_diagnostic(self):
        lab = {'a': 1, 'prompt_chars': 99, 'b': 2}
        self.assertEqual(AF._label_without_diagnostic(lab), {'a': 1, 'b': 2})

    def test_compute_amendment_real(self):
        v3, changed, built, proofs = AF.compute_amendment(ROOT / AF.V2_REL)
        self.assertEqual(v3['freeze_version'], 3)
        self.assertIn(AF.JUDGE_REL, changed)
        self.assertEqual(len(v3['amendment']['changed_label_files']), 23)
        self.assertTrue(v3['amendment']['on_disk_silver_labels_modified'])
        self.assertTrue(v3['amendment']['scoring_content_unchanged'])
        self.assertEqual(v3['amendment']['judge_version'], {'old': '1.0.0', 'new': '1.1.0'})
        for cid, pr in proofs.items():
            self.assertNotEqual(pr['old_prompt_chars'], pr['new_prompt_chars'])

    def test_dry_run_exit0(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'v3.json'
            self.assertEqual(AF.main(['--dry-run', '--output', str(out)]), 0)
            self.assertFalse(out.exists())

    def test_overwrite_refusal(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'v3.json'
            out.write_text('{}', encoding='utf-8')
            self.assertEqual(AF.main(['--output', str(out)]), 3)

    def test_parent_version_guard(self):
        with tempfile.TemporaryDirectory() as td:
            v2 = Path(td) / 'v2.json'
            v2.write_text(json.dumps({'freeze_version': 1}), encoding='utf-8')
            with self.assertRaises(ValueError):
                AF.compute_amendment(v2)


class ProbesP1Tests(unittest.TestCase):
    def test_dry_run_no_calls(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'probe.json'
            rc = PP.main([str(ROOT / 'samples/calibration_manifest.json'), '--output', str(out), '--probe', 'position', '--dry-run'])
            self.assertEqual(rc, 0)
            self.assertFalse(out.exists())

    def test_probe_subset_dev_only(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cases = []
            for cid in PP.PROBE_SUBSET:
                (tmp / (cid + '.html')).write_text(SOURCE.replace('</main>', '<p>' + cid + '</p></main>'), encoding='utf-8')
                cases.append({'case_id': cid, 'template': 't', 'split': 'development', 'source': cid + '.html', 'candidate': 'extract'})
            mp = tmp / 'manifest.json'
            mp.write_text(json.dumps({'judge_manifest_version': 1, 'cases': cases}), encoding='utf-8')
            prov = Provider()
            rep = PP.run_probe_batch(mp, prov, model='qwen3.8-27b', probe_key='position', max_calls=6,
                                     cache_path=tmp / 'cache.json', report_path=tmp / 'report.json')
            self.assertEqual(rep['probe_key'], 'position')
            self.assertEqual(rep['probe'], {'source_order_seed': PP.POSITION_SEED})
            self.assertEqual(len(rep['cases']), 6)
            self.assertTrue(all(r['split'] == 'development' for r in rep['cases']))
            self.assertIn('DESCRIPTIVE ONLY', rep['note'])
            self.assertEqual(prov.calls, 6)

    def test_probe_subset_missing_raises(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / 'page.html').write_text(SOURCE, encoding='utf-8')
            mp = tmp / 'manifest.json'
            mp.write_text(json.dumps({'judge_manifest_version': 1, 'cases': [
                {'case_id': 'cal-appetite-clean', 'template': 't', 'split': 'development', 'source': 'page.html', 'candidate': 'extract'}]}), encoding='utf-8')
            with self.assertRaises(ValueError):
                PP.run_probe_batch(mp, Provider(), model='qwen3.8-27b', probe_key='position', cache_path=tmp / 'c.json')

    def test_stability_config_ignore_cache(self):
        self.assertTrue(PP.PROBES['stability']['ignore_cache'])
        self.assertIsNone(PP.PROBES['stability']['probe'])


class ScoreP1Tests(unittest.TestCase):
    def _rows(self, pairs):
        rows = []
        for cid, jd, js, jsev, hd, hs, hsev, status in pairs:
            row = mkrow(cid, 'development', decision=jd, sev=jsev, score=js, status=status)
            entry = mkgold(cid, decision=hd, sev=hsev, score=hs)
            r, _ = compare_human_case(row, entry, None)
            rows.append(r)
        return rows

    def test_acceptance_accept(self):
        rows = self._rows([('c1', 'fail', 2, 'major', 'fail', 2, 'major', 'accepted'),
                           ('c2', 'fail', 2, 'major', 'fail', 2, 'major', 'accepted')])
        agg = aggregate_human(rows)
        a = SP._acceptance(rows, agg)
        self.assertEqual(a['verdict'], 'ACCEPT')
        self.assertEqual(a['reject_rate'], 0.0)

    def test_acceptance_reject_high_rejection(self):
        rows = self._rows([('c1', 'fail', 2, 'major', 'fail', 2, 'major', 'accepted'),
                           ('c2', 'fail', 2, 'major', 'fail', 2, 'major', 'error')])
        a = SP._acceptance(rows, aggregate_human(rows))
        self.assertEqual(a['verdict'], 'REJECT')
        self.assertFalse(a['checks']['reject_rate_lt_0.10'])

    def test_acceptance_reject_severe_miss(self):
        rows = self._rows([('c1', 'pass', 4, 'none', 'fail', 2, 'major', 'accepted'),
                           ('c2', 'pass', 4, 'none', 'fail', 2, 'major', 'accepted')])
        a = SP._acceptance(rows, aggregate_human(rows))
        self.assertEqual(a['severe_miss_count'], 2)
        self.assertEqual(a['verdict'], 'REJECT')

    def test_acceptance_reject_mismatch(self):
        rows = self._rows([('c1', 'pass', 4, 'none', 'uncertain', 3, 'minor', 'accepted'),
                           ('c2', 'pass', 4, 'none', 'uncertain', 3, 'minor', 'accepted')])
        a = SP._acceptance(rows, aggregate_human(rows))
        self.assertEqual(a['accepted_decision_mismatches'], 2)
        self.assertEqual(a['severe_miss_count'], 0)
        self.assertEqual(a['verdict'], 'REJECT')

    def test_gold_map_list_and_dict(self):
        g = [{'case_id': 'c1', 'decision': 'fail'}]
        self.assertEqual(SP._gold_map({'cases': g})['c1']['decision'], 'fail')
        self.assertEqual(SP._gold_map({'cases': {'c1': {'case_id': 'c1', 'decision': 'pass'}}})['c1']['decision'], 'pass')

    def test_cross_judge_agreement(self):
        batch = {'cases': [mkrow('c1', 'development', decision='fail', sev='major', score=2)]}
        cross = {'signature': {'model': 'qwen-max'}, 'cases': [mkrow('c1', 'development', decision='fail', sev='major', score=2)]}
        cj = SP._cross_judge(batch, cross, ROOT / 'samples/calibration/labels')
        self.assertEqual(cj['model2'], 'qwen-max')
        self.assertEqual(cj['both_accepted'], 1)
        self.assertEqual(cj['agreement']['decision_match_rate'], 1.0)

    def test_probe_stability_flip(self):
        batch = {'cases': [mkrow('c1', 'development', decision='fail', sev='major', score=2)]}
        probe = {'probe_key': 'position', 'cases': [mkrow('c1', 'development', decision='uncertain', sev='minor', score=3)]}
        st = SP._probe_stability(batch, probe)
        self.assertEqual(st['n_comparable_cases'], 1)
        self.assertEqual(st['decision_flip_rate'], 1.0)

    def test_dev_only_guard(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            batch = {'split_filter': 'development', 'cases': [mkrow('c1', 'frozen_test', decision='fail', sev='major', score=2)]}
            bp = tmp / 'batch.json'; bp.write_text(json.dumps(batch), encoding='utf-8')
            gold = {'cases': [mkgold('c1', 'fail', 2, 'major')]}
            gp = tmp / 'gold.json'; gp.write_text(json.dumps(gold), encoding='utf-8')
            out = tmp / 'out.json'
            rc = SP.main(['--batch', str(bp), '--gold', str(gp), '--output', str(out),
                          '--freeze', str(ROOT / 'outputs/rubrics_judge.node3.freeze.v2.json')])
            self.assertEqual(rc, 2)
            self.assertFalse(out.exists())


class ScoreP1MainTests(unittest.TestCase):
    FREEZE = ROOT / 'outputs/rubrics_judge.node3.freeze.v3.json'
    MANIFEST = ROOT / 'samples/calibration_manifest.json'

    def _batch(self, rows):
        return {'tool': 'run_rubrics_judge.py', 'split_filter': 'development',
                'manifest_sha256': 'synthetic', 'signature': {'model': 'qwen3.8-27b', 'judge_version': '1.1.0'},
                'cases': rows}

    def _files(self, tmp, batch, gold):
        bp = tmp / 'batch.json'; bp.write_text(json.dumps(batch), encoding='utf-8')
        gp = tmp / 'gold.json'; gp.write_text(json.dumps(gold), encoding='utf-8')
        return bp, gp

    def test_main_accept_writes_report_and_md(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            batch = self._batch([mkrow('c1', 'development', decision='fail', sev='major', score=2),
                                 mkrow('c2', 'development', decision='fail', sev='major', score=2)])
            gold = {'cases': [mkgold('c1', 'fail', 2, 'major'), mkgold('c2', 'fail', 2, 'major')]}
            bp, gp = self._files(tmp, batch, gold)
            out = tmp / 'out.json'; md = tmp / 'out.md'
            rc = SP.main(['--batch', str(bp), '--gold', str(gp), '--output', str(out), '--md', str(md),
                          '--freeze', str(self.FREEZE), '--manifest', str(self.MANIFEST)])
            self.assertEqual(rc, 0)
            self.assertTrue(out.exists()); self.assertTrue(md.exists())
            res = json.loads(out.read_text(encoding='utf-8'))
            self.assertEqual(res['acceptance']['verdict'], 'ACCEPT')
            self.assertEqual(res['scope'], 'development_only')
            self.assertIn('P1 development acceptance', md.read_text(encoding='utf-8'))

    def test_main_reject_exit2(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            batch = self._batch([mkrow('c1', 'development', decision='fail', sev='major', score=2),
                                 mkrow('c2', 'development', decision='fail', sev='major', score=2, status='error')])
            gold = {'cases': [mkgold('c1', 'fail', 2, 'major'), mkgold('c2', 'fail', 2, 'major')]}
            bp, gp = self._files(tmp, batch, gold)
            out = tmp / 'out.json'
            rc = SP.main(['--batch', str(bp), '--gold', str(gp), '--output', str(out),
                          '--freeze', str(self.FREEZE), '--manifest', str(self.MANIFEST)])
            self.assertEqual(rc, 2)
            res = json.loads(out.read_text(encoding='utf-8'))
            self.assertEqual(res['acceptance']['verdict'], 'REJECT')
            self.assertFalse(res['acceptance']['checks']['reject_rate_lt_0.10'])

    def test_main_with_cross_and_probes(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            batch = self._batch([mkrow('c1', 'development', decision='fail', sev='major', score=2)])
            gold = {'cases': [mkgold('c1', 'fail', 2, 'major')]}
            bp, gp = self._files(tmp, batch, gold)
            cross = tmp / 'cross.json'
            cross.write_text(json.dumps({'signature': {'model': 'qwen-max'},
                                         'cases': [mkrow('c1', 'development', decision='fail', sev='major', score=2)]}), encoding='utf-8')
            probe = tmp / 'probe.json'
            probe.write_text(json.dumps({'probe_key': 'position',
                                         'cases': [mkrow('c1', 'development', decision='uncertain', sev='minor', score=3)]}), encoding='utf-8')
            out = tmp / 'out.json'
            rc = SP.main(['--batch', str(bp), '--gold', str(gp), '--output', str(out),
                          '--cross', str(cross), '--probe-position', str(probe),
                          '--freeze', str(self.FREEZE), '--manifest', str(self.MANIFEST)])
            self.assertEqual(rc, 0)
            res = json.loads(out.read_text(encoding='utf-8'))
            self.assertEqual(res['cross_judge']['model2'], 'qwen-max')
            self.assertEqual(res['cross_judge']['both_accepted'], 1)
            self.assertEqual(res['probes']['position']['decision_flip_rate'], 1.0)

    def test_main_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            batch = self._batch([mkrow('c1', 'development', decision='fail', sev='major', score=2)])
            gold = {'cases': [mkgold('c1', 'fail', 2, 'major')]}
            bp, gp = self._files(tmp, batch, gold)
            out = tmp / 'out.json'; out.write_text('{}', encoding='utf-8')
            rc = SP.main(['--batch', str(bp), '--gold', str(gp), '--output', str(out),
                          '--freeze', str(self.FREEZE), '--manifest', str(self.MANIFEST)])
            self.assertEqual(rc, 3)


if __name__ == '__main__':
    unittest.main()
