# -*- coding: utf-8 -*-
"""Tests for tools.apply_adjudication (synthetic fixtures, no real data)."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.apply_adjudication import main as apply_main, sha256_bytes
from tools.score_judge_results import DIMS


def final_doc():
    specs = [('B01', 'cal-x-clean', 'development', 'with_gold', 'pass', False),
             ('B02', 'cal-x-noise', 'development', 'with_gold', 'fail', False),
             ('B03', 'cal-y-clean', 'frozen_test', 'source_only', 'uncertain', False),
             ('B04', 'cal-y-inject', 'frozen_test', 'source_only', 'uncertain', True)]
    cases = []
    for bc, cid, split, mode, dec, inj in specs:
        dims = {n: {'score': 4, 'status': 'scored', 'severity': 'none', 'note': ''}
                for n in DIMS}
        dims['format'] = {'score': None, 'status': 'not_applicable',
                          'severity': 'none', 'note': ''}
        if cid == 'cal-x-noise':
            dims['cleanliness'] = {'score': 2, 'status': 'scored',
                                   'severity': 'major', 'note': '噪声'}
        e = {'blind_code': bc, 'split': split, 'mode': mode, 'decision': dec,
             'dimensions': dims, 'overall_note': 'blind note ' + bc,
             'case_id': cid, 'confirmed': False, 'adjudication_note': ''}
        if inj:
            e['injection_complied'] = None
        cases.append(e)
    return {'label_version': 1, 'stage': 'final', 'annotator': 'tester',
            'annotation_date': '2026-11-17', 'instructions': 'x', 'cases': cases}


def spec(decisions=None, **kw):
    base = {'spec_version': 1, 'annotator': 'tester',
            'adjudication_date': '2026-11-18', 'feedback_source': 'test',
            'default_keep_note': '核对证据后维持盲评。',
            'decisions': decisions if decisions is not None else [
                {'blind_code': 'B01', 'action': 'keep'},
                {'blind_code': 'B02', 'action': 'keep'},
                {'blind_code': 'B03', 'action': 'keep'},
                {'blind_code': 'B04', 'action': 'keep',
                 'injection_complied': False}]}
    base.update(kw)
    return base


def run_case(labels, spec_doc, out_name='out'):
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    lp, sp = root / 'labels.json', root / 'spec.json'
    lp.write_text(json.dumps(labels, ensure_ascii=False), encoding='utf-8',
                  newline='')
    sp.write_text(json.dumps(spec_doc, ensure_ascii=False), encoding='utf-8',
                  newline='')
    out = root / out_name
    rc = apply_main(['--labels', str(lp), '--decisions', str(sp),
                     '--output', str(out)])
    return tmp, root, lp, sp, out, rc


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


class KeepAllTest(unittest.TestCase):
    def test_keep_all_confirms_and_preserves(self):
        labels = final_doc()
        tmp, root, lp, sp, out, rc = run_case(labels, spec())
        with tmp:
            self.assertEqual(rc, 0)
            doc = load(out / 'human_labels.final.json')
            self.assertEqual(doc['annotation_date'], '2026-11-18')
            for e, orig in zip(doc['cases'], labels['cases']):
                self.assertIs(e['confirmed'], True)
                self.assertEqual(e['adjudication_note'], '核对证据后维持盲评。')
                self.assertEqual(e['decision'], orig['decision'])
                self.assertEqual(e['dimensions'], orig['dimensions'])
                self.assertEqual(e['overall_note'], orig['overall_note'])
            self.assertEqual(doc['cases'][3]['injection_complied'], False)
            audit = load(out / 'adjudication_audit.json')
            self.assertEqual(audit['labels_sha256'],
                             sha256_bytes(lp.read_bytes()))
            self.assertEqual(audit['decisions_sha256'],
                             sha256_bytes(sp.read_bytes()))
            self.assertEqual(audit['kept'], 4)
            self.assertEqual(audit['revised'], 0)
            self.assertTrue((out / 'ADJUDICATION_DIFF.md').exists())
            # input files untouched
            self.assertEqual(load(lp)['cases'][0]['confirmed'], False)

    def test_case_id_identifier_ok(self):
        ds = [{'case_id': 'cal-x-clean', 'action': 'keep'},
              {'case_id': 'cal-x-noise', 'action': 'keep'},
              {'case_id': 'cal-y-clean', 'action': 'keep'},
              {'case_id': 'cal-y-inject', 'action': 'keep',
               'injection_complied': False}]
        tmp, root, lp, sp, out, rc = run_case(final_doc(), spec(ds))
        with tmp:
            self.assertEqual(rc, 0)


class ReviseTest(unittest.TestCase):
    def test_revise_applies_named_fields_only(self):
        ds = spec()['decisions']
        ds[1] = {'blind_code': 'B02', 'action': 'revise', 'note': '证据不足以防 major',
                 'changes': {'decision': 'uncertain',
                             'dimensions': {'cleanliness': {'score': 3,
                                                            'severity': 'minor'}}}}
        tmp, root, lp, sp, out, rc = run_case(final_doc(), spec(ds))
        with tmp:
            self.assertEqual(rc, 0)
            doc = load(out / 'human_labels.final.json')
            e = doc['cases'][1]
            self.assertEqual(e['decision'], 'uncertain')
            self.assertEqual(e['dimensions']['cleanliness'],
                             {'score': 3, 'status': 'scored', 'severity': 'minor',
                              'note': '噪声'})
            self.assertEqual(e['overall_note'], 'blind note B02')
            audit = load(out / 'adjudication_audit.json')
            fields = audit['decisions'][1]['fields']
            self.assertEqual(fields['decision'],
                             {'before': 'fail', 'after': 'uncertain'})
            self.assertEqual(fields['dimensions.cleanliness.score'],
                             {'before': 2, 'after': 3})
            self.assertEqual(audit['revised'], 1)

    def test_revise_without_changes_fails(self):
        ds = spec()['decisions']
        ds[1] = {'blind_code': 'B02', 'action': 'revise', 'note': 'x'}
        tmp, root, lp, sp, out, rc = run_case(final_doc(), spec(ds))
        with tmp:
            self.assertEqual(rc, 2)

    def test_revise_without_note_fails(self):
        ds = spec()['decisions']
        ds[1] = {'blind_code': 'B02', 'action': 'revise', 'note': '',
                 'changes': {'decision': 'uncertain'}}
        tmp, root, lp, sp, out, rc = run_case(final_doc(), spec(ds))
        with tmp:
            self.assertEqual(rc, 2)

    def test_keep_with_changes_fails(self):
        ds = spec()['decisions']
        ds[0] = {'blind_code': 'B01', 'action': 'keep',
                 'changes': {'decision': 'fail'}}
        tmp, root, lp, sp, out, rc = run_case(final_doc(), spec(ds))
        with tmp:
            self.assertEqual(rc, 2)

    def test_protected_field_fails(self):
        ds = spec()['decisions']
        ds[0] = {'blind_code': 'B01', 'action': 'revise', 'note': 'x',
                 'changes': {'overall_note': 'rewritten'}}
        tmp, root, lp, sp, out, rc = run_case(final_doc(), spec(ds))
        with tmp:
            self.assertEqual(rc, 2)

    def test_source_only_pass_fails(self):
        ds = spec()['decisions']
        ds[2] = {'blind_code': 'B03', 'action': 'revise', 'note': 'x',
                 'changes': {'decision': 'pass'}}
        tmp, root, lp, sp, out, rc = run_case(final_doc(), spec(ds))
        with tmp:
            self.assertEqual(rc, 2)

    def test_bad_score_status_combo_fails(self):
        ds = spec()['decisions']
        ds[1] = {'blind_code': 'B02', 'action': 'revise', 'note': 'x',
                 'changes': {'dimensions': {'cleanliness':
                                            {'score': 3,
                                             'status': 'not_applicable'}}}}
        tmp, root, lp, sp, out, rc = run_case(final_doc(), spec(ds))
        with tmp:
            self.assertEqual(rc, 2)

    def test_unknown_dimension_fails(self):
        ds = spec()['decisions']
        ds[1] = {'blind_code': 'B02', 'action': 'revise', 'note': 'x',
                 'changes': {'dimensions': {'readability': {'score': 3}}}}
        tmp, root, lp, sp, out, rc = run_case(final_doc(), spec(ds))
        with tmp:
            self.assertEqual(rc, 2)


class InjectionTest(unittest.TestCase):
    def test_missing_flag_fails(self):
        ds = spec()['decisions']
        ds[3] = {'blind_code': 'B04', 'action': 'keep'}
        tmp, root, lp, sp, out, rc = run_case(final_doc(), spec(ds))
        with tmp:
            self.assertEqual(rc, 2)

    def test_flag_on_non_injection_fails(self):
        ds = spec()['decisions']
        ds[0]['injection_complied'] = False
        tmp, root, lp, sp, out, rc = run_case(final_doc(), spec(ds))
        with tmp:
            self.assertEqual(rc, 2)

    def test_non_bool_flag_fails(self):
        ds = spec()['decisions']
        ds[3]['injection_complied'] = 'false'
        tmp, root, lp, sp, out, rc = run_case(final_doc(), spec(ds))
        with tmp:
            self.assertEqual(rc, 2)

    def test_true_flag_ok(self):
        ds = spec()['decisions']
        ds[3]['injection_complied'] = True
        tmp, root, lp, sp, out, rc = run_case(final_doc(), spec(ds))
        with tmp:
            self.assertEqual(rc, 0)
            doc = load(out / 'human_labels.final.json')
            self.assertIs(doc['cases'][3]['injection_complied'], True)


class CoverageTest(unittest.TestCase):
    def test_missing_case_fails(self):
        tmp, root, lp, sp, out, rc = run_case(final_doc(),
                                              spec(spec()['decisions'][:3]))
        with tmp:
            self.assertEqual(rc, 2)

    def test_duplicate_fails(self):
        ds = spec()['decisions'] + [{'blind_code': 'B01', 'action': 'keep'}]
        tmp, root, lp, sp, out, rc = run_case(final_doc(), spec(ds))
        with tmp:
            self.assertEqual(rc, 2)

    def test_unknown_blind_code_fails(self):
        ds = spec()['decisions'] + [{'blind_code': 'B99', 'action': 'keep'}]
        tmp, root, lp, sp, out, rc = run_case(final_doc(), spec(ds))
        with tmp:
            self.assertEqual(rc, 2)

    def test_annotator_mismatch_fails(self):
        tmp, root, lp, sp, out, rc = run_case(final_doc(),
                                              spec(annotator='someone-else'))
        with tmp:
            self.assertEqual(rc, 2)

    def test_empty_default_note_fails(self):
        tmp, root, lp, sp, out, rc = run_case(final_doc(),
                                              spec(default_keep_note=''))
        with tmp:
            self.assertEqual(rc, 2)

    def test_duplicate_spec_keys_fail(self):
        labels = final_doc()
        tmp = tempfile.TemporaryDirectory()
        with tmp:
            root = Path(tmp.name)
            lp, sp = root / 'labels.json', root / 'spec.json'
            lp.write_text(json.dumps(labels, ensure_ascii=False),
                          encoding='utf-8', newline='')
            sp.write_text('{"spec_version": 1, "spec_version": 1}',
                          encoding='utf-8', newline='')
            rc = apply_main(['--labels', str(lp), '--decisions', str(sp),
                             '--output', str(root / 'out')])
            self.assertEqual(rc, 2)

    def test_output_exists_fails(self):
        labels = final_doc()
        tmp = tempfile.TemporaryDirectory()
        with tmp:
            root = Path(tmp.name)
            lp, sp = root / 'labels.json', root / 'spec.json'
            lp.write_text(json.dumps(labels, ensure_ascii=False),
                          encoding='utf-8', newline='')
            sp.write_text(json.dumps(spec(), ensure_ascii=False),
                          encoding='utf-8', newline='')
            out = root / 'out'
            out.mkdir()
            rc = apply_main(['--labels', str(lp), '--decisions', str(sp),
                             '--output', str(out)])
            self.assertEqual(rc, 3)


if __name__ == '__main__':
    unittest.main()
