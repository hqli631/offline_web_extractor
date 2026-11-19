# -*- coding: utf-8 -*-
"""Tests for tools.repair_human_labels and for blind-code-only error reporting."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.ingest_human_labels import validate_labels
from tools.repair_human_labels import (GAP_KIND, apply_changes, apply_overrides,
                                       consistency_warnings, derive_severity,
                                       main as repair_main, note_text, pending,
                                       repair, validate_overrides)
from tools.score_judge_results import DIMS, load_json
from tests.human_review_fixtures import human_doc, make_fixture

MAP = str(Path(__file__).resolve().parents[1] / 'configs' / 'severity_keyword_map.v1.json')


def dim(score, status, severity, note=''):
    return {'score': score, 'status': status, 'severity': severity, 'note': note}


def blind_doc(cases, annotator='tester', date='2026-11-17'):
    return {'label_version': 1, 'stage': 'blind', 'annotator': annotator,
            'annotation_date': date, 'cases': cases}


def case(blind_code, decision, overall_note='', dims=None):
    d = {n: dim(4, 'scored', 'none') for n in DIMS}
    d['format'] = dim(None, 'not_applicable', 'none')
    d.update(dims or {})
    return {'blind_code': blind_code, 'split': 'development', 'mode': 'with_gold',
            'decision': decision, 'dimensions': d, 'overall_note': overall_note}


def cfg():
    return load_json(MAP)


class DeriveSeverityTest(unittest.TestCase):
    def test_no_keyword_is_none(self):
        sev, rule = derive_severity('cleanliness', '源截断：是', cfg())
        self.assertEqual(sev, 'none')
        self.assertIsNone(rule)

    def test_noise_keyword_is_major(self):
        sev, _ = derive_severity('cleanliness', '将非正文的推荐内容提取出来', cfg())
        self.assertEqual(sev, 'major')

    def test_duplicate_keyword_is_major(self):
        self.assertEqual(derive_severity('cleanliness', '存在段落重复提取', cfg())[0], 'major')

    def test_missing_keyword_is_major(self):
        self.assertEqual(derive_severity('completeness', '第一段正文未被提取出来', cfg())[0],
                         'major')

    def test_reorder_keyword_is_major(self):
        self.assertEqual(derive_severity('structure', '存在段落提取颠倒', cfg())[0], 'major')

    def test_tag_leak_keyword_is_major(self):
        self.assertEqual(derive_severity('structure', '将<、ul>这类结构符号提取了出来', cfg())[0],
                         'major')

    def test_major_beats_minor_in_same_dim(self):
        text = '存在段落位置颠倒，存在原文的一段被分成多段的情况'
        self.assertEqual(derive_severity('structure', text, cfg())[0], 'major')

    def test_split_only_is_minor(self):
        self.assertEqual(derive_severity('structure', '一段被分成多段', cfg())[0], 'minor')

    def test_dim_rules_are_scoped(self):
        self.assertEqual(derive_severity('title', '存在段落重复提取', cfg())[0], 'none')

    def test_format_has_no_rules(self):
        self.assertEqual(derive_severity('format', '非正文 重复 颠倒 遗漏 标题', cfg())[0], 'none')


class RepairTest(unittest.TestCase):
    def test_misplaced_partial_becomes_status_on_truncated_case(self):
        doc = blind_doc([case('B01', 'uncertain', '源截断：是',
                              {'completeness': dim(4, 'scored', 'partial')})])
        changes, kept, flags = repair(doc, cfg())
        self.assertEqual(len(changes), 1)
        c = changes[0]
        self.assertEqual((c['status_before'], c['status_after']), ('scored', 'partial'))
        self.assertEqual((c['severity_before'], c['severity_after']), ('partial', 'none'))
        self.assertEqual(c['kind'], 'misplaced_partial')
        self.assertEqual([k['dim'] for k in kept], ['cleanliness', 'structure', 'title', 'format'])
        self.assertTrue(any(f['flag'] == 'low_confidence_case' for f in flags))

    def test_misplaced_partial_without_low_confidence_keeps_scored(self):
        doc = blind_doc([case('B01', 'uncertain', '存在原文的一段被分成多段的情况',
                              {'structure': dim(3, 'scored', 'partial')})])
        changes, _, flags = repair(doc, cfg())
        self.assertEqual(changes[0]['status_after'], 'scored')
        self.assertEqual(changes[0]['severity_after'], 'minor')
        self.assertFalse(any(f['flag'] == 'low_confidence_case' for f in flags))

    def test_misplaced_partial_uses_annotator_keyword(self):
        doc = blind_doc([case('B01', 'fail', '将非正文的编辑信息提取出来，且是源截断',
                              {'cleanliness': dim(3, 'scored', 'partial')})])
        changes, _, _ = repair(doc, cfg())
        self.assertEqual(changes[0]['severity_after'], 'major')
        self.assertEqual(changes[0]['keyword_hit'], '非正文')

    def test_legal_severity_is_never_touched(self):
        doc = blind_doc([case('B01', 'fail', '段落乱序',
                              {'structure': dim(2, 'scored', 'major')})])
        changes, kept, flags = repair(doc, cfg())
        self.assertEqual(changes, [])
        self.assertEqual(len(kept), 5)
        self.assertFalse(any(f['flag'] == 'unrepairable_severity' for f in flags))

    def test_critical_with_high_score_is_flagged_not_changed(self):
        doc = blind_doc([case('B01', 'fail', '正文内容提取少很多',
                              {'completeness': dim(2, 'scored', 'critical')})])
        changes, _, flags = repair(doc, cfg())
        self.assertEqual(changes, [])
        self.assertTrue(any(f['flag'] == 'critical_with_nonzero_score' and f['dim'] == 'completeness'
                            for f in flags))

    def test_critical_with_low_score_is_not_flagged(self):
        doc = blind_doc([case('B01', 'fail', '空候选',
                              {'completeness': dim(0, 'scored', 'critical')})])
        _, _, flags = repair(doc, cfg())
        self.assertFalse(any(f['flag'] == 'critical_with_nonzero_score' for f in flags))

    def test_unknown_severity_is_flagged_unrepairable(self):
        doc = blind_doc([case('B01', 'uncertain', '', {'title': dim(None, 'unscored', 'bogus')})])
        changes, _, flags = repair(doc, cfg())
        self.assertEqual(changes, [])
        self.assertTrue(any(f['flag'] == 'unrepairable_severity' for f in flags))

    def test_per_dimension_note_is_also_considered(self):
        c = case('B01', 'fail', '')
        c['dimensions']['cleanliness'] = dim(3, 'scored', 'partial', '重复段落混入')
        changes, _, _ = repair(blind_doc([c]), cfg())
        self.assertEqual(changes[0]['severity_after'], 'major')

    def test_note_text_collects_all_notes(self):
        c = case('B01', 'fail', 'OVERALL')
        c['dimensions']['title'] = dim(3, 'scored', 'none', 'DIMNOTE')
        text = note_text(c)
        self.assertIn('OVERALL', text)
        self.assertIn('DIMNOTE', text)


class ApplyTest(unittest.TestCase):
    def setUp(self):
        self.doc = blind_doc([
            case('B01', 'fail', '将非正文的编辑信息提取出来，且是源截断',
                 {'cleanliness': dim(3, 'scored', 'partial'),
                  'structure': dim(2, 'scored', 'major')}),
            case('B02', 'pass', 'p 块和 g 块完全相同'),
        ])
        self.doc['cases'][0]['dimensions']['title']['note'] = 'KEEPME'
        self.changes, self.kept, self.flags = repair(self.doc, cfg())

    def test_score_decision_and_notes_are_preserved(self):
        out = apply_changes(self.doc, self.changes)
        for before, after in zip(self.doc['cases'], out['cases']):
            self.assertEqual(before['decision'], after['decision'])
            self.assertEqual(before['overall_note'], after['overall_note'])
            self.assertEqual(before['blind_code'], after['blind_code'])
            for n in DIMS:
                self.assertEqual(before['dimensions'][n]['score'], after['dimensions'][n]['score'])
        self.assertEqual(out['cases'][0]['dimensions']['title']['note'], 'KEEPME')

    def test_original_document_is_not_mutated(self):
        snapshot = json.dumps(self.doc, ensure_ascii=False, sort_keys=True)
        apply_changes(self.doc, self.changes)
        self.assertEqual(snapshot, json.dumps(self.doc, ensure_ascii=False, sort_keys=True))

    def test_applied_output_uses_legal_enums(self):
        out = apply_changes(self.doc, self.changes)
        for c in out['cases']:
            for n in DIMS:
                v = c['dimensions'][n]
                self.assertIn(v['severity'], ('none', 'minor', 'major', 'critical', 'unknown'))
                self.assertIn(v['status'], ('scored', 'partial', 'unscored', 'not_applicable'))
                if v['score'] is None:
                    self.assertIn(v['status'], ('unscored', 'not_applicable'))
                else:
                    self.assertIn(v['status'], ('scored', 'partial'))

    def test_untouched_dimension_keeps_user_severity(self):
        out = apply_changes(self.doc, self.changes)
        self.assertEqual(out['cases'][0]['dimensions']['structure']['severity'], 'major')
        self.assertEqual(out['cases'][0]['dimensions']['structure']['status'], 'scored')

    def test_repair_metadata_is_recorded(self):
        out = apply_changes(self.doc, self.changes)
        self.assertEqual(out['repair']['applied'], len(self.changes))


class ConsistencyWarningTest(unittest.TestCase):
    def warns(self, doc, changes=None):
        sev_after = {(c['blind_code'], c['dim']): c['severity_after'] for c in (changes or [])}
        return consistency_warnings(doc, lambda k, cur: sev_after.get(k, cur))

    def test_fail_without_severe_is_flagged(self):
        doc = blind_doc([case('B01', 'fail', '一段被分成多段',
                              {'structure': dim(3, 'scored', 'minor')})])
        kinds = [w[2] for w in self.warns(doc)]
        self.assertIn('decision_fail_without_major_or_critical', kinds)

    def test_severe_but_not_fail_is_flagged(self):
        doc = blind_doc([case('B01', 'uncertain', '非正文混入',
                              {'cleanliness': dim(3, 'scored', 'major')})])
        self.assertIn('major_or_critical_but_not_fail', [w[2] for w in self.warns(doc)])

    def test_pass_with_defect_is_flagged(self):
        doc = blind_doc([case('B01', 'pass', '', {'title': dim(3, 'scored', 'minor')})])
        self.assertIn('pass_with_defect', [w[2] for w in self.warns(doc)])

    def test_pass_with_partial_status_is_flagged(self):
        doc = blind_doc([case('B01', 'pass', '', {'title': dim(4, 'partial', 'none')})])
        self.assertIn('pass_with_low_confidence', [w[2] for w in self.warns(doc)])

    def test_consistent_case_has_no_warning(self):
        doc = blind_doc([case('B01', 'fail', '段落乱序', {'structure': dim(2, 'scored', 'major')}),
                         case('B02', 'pass', '完全相同')])
        self.assertEqual(self.warns(doc), [])

    def test_repaired_severity_is_used_for_warnings(self):
        doc = blind_doc([case('B01', 'uncertain', '非正文的备注内容，且是源截断',
                              {'cleanliness': dim(3, 'scored', 'partial')})])
        changes, _, _ = repair(doc, cfg())
        self.assertEqual(self.warns(doc), [])
        self.assertIn('major_or_critical_but_not_fail',
                      [w[2] for w in self.warns(doc, changes)])


class CliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.labels = self.root / 'human_labels.blind.json'
        doc = blind_doc([case('B01', 'fail', '将非正文的编辑信息提取出来，且是源截断',
                              {'cleanliness': dim(3, 'scored', 'partial')}),
                         case('B02', 'pass', 'p 块和 g 块完全相同')])
        self.labels.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                               encoding='utf-8', newline='')

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, out_name, apply=False, labels=None):
        argv = ['--labels', str(labels or self.labels),
                '--map', MAP, '--output', str(self.root / out_name)]
        if apply:
            argv.append('--apply')
        return repair_main(argv)

    def test_dry_run_reports_only(self):
        self.assertEqual(self.run_cli('prep'), 0)
        out = self.root / 'prep'
        self.assertTrue((out / 'REPAIR_DIFF.md').exists())
        self.assertTrue((out / 'CONSISTENCY_WARNINGS.md').exists())
        self.assertTrue((out / 'severity_repairs.json').exists())
        self.assertTrue((out / 'repair_audit.json').exists())
        self.assertFalse((out / 'human_labels.blind.r2.json').exists())
        audit = load_json(out / 'repair_audit.json')
        self.assertFalse(audit['applied'])
        self.assertEqual(audit['n_changes'], 1)

    def test_apply_writes_repaired_labels(self):
        self.assertEqual(self.run_cli('prep2', apply=True), 0)
        r2 = load_json(self.root / 'prep2' / 'human_labels.blind.r2.json')
        self.assertEqual(r2['cases'][0]['dimensions']['cleanliness']['severity'], 'major')
        self.assertEqual(r2['cases'][0]['dimensions']['cleanliness']['status'], 'partial')
        self.assertTrue(load_json(self.root / 'prep2' / 'repair_audit.json')['applied'])

    def test_source_file_is_never_modified(self):
        before = self.labels.read_bytes()
        self.run_cli('prep3', apply=True)
        self.assertEqual(before, self.labels.read_bytes())

    def test_refuses_existing_output_dir(self):
        self.assertEqual(self.run_cli('prep4'), 0)
        self.assertEqual(self.run_cli('prep4'), 3)

    def test_refuses_labels_that_contain_case_id(self):
        doc = load_json(self.labels)
        doc['cases'][0]['case_id'] = 'cal-mdn-noise'
        leaked = self.root / 'leaked.json'
        leaked.write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8', newline='')
        self.assertEqual(self.run_cli('prep5', labels=leaked), 2)
        self.assertFalse((self.root / 'prep5').exists())

    def test_refuses_non_blind_stage(self):
        doc = load_json(self.labels)
        doc['stage'] = 'final'
        p = self.root / 'final.json'
        p.write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8', newline='')
        self.assertEqual(self.run_cli('prep6', labels=p), 2)

    def test_reports_contain_no_real_case_id_or_mutation_type(self):
        self.run_cli('prep7', apply=True)
        forbidden = ['cal-mdn', 'cal-blurb', 'cal-github', 'cal-iana', 'cal-w3clink',
                     'cal-appetite', 'reorder', 'missing_paragraph', 'instruction_interference',
                     'code_indent', 'case_id', 'JUDGE_REASON_SENTINEL', 'assistant_silver']
        for name in ('REPAIR_DIFF.md', 'CONSISTENCY_WARNINGS.md', 'severity_repairs.json',
                     'repair_audit.json', 'human_labels.blind.r2.json'):
            text = (self.root / 'prep7' / name).read_text(encoding='utf-8')
            for bad in forbidden:
                self.assertNotIn(bad, text, '%s leaked %r' % (name, bad))

    def test_repair_diff_is_deterministic(self):
        self.run_cli('det1')
        self.run_cli('det2')
        a = (self.root / 'det1' / 'REPAIR_DIFF.md').read_bytes()
        b = (self.root / 'det2' / 'REPAIR_DIFF.md').read_bytes()
        self.assertEqual(a, b)


class BlindCodeErrorReportingTest(unittest.TestCase):
    """Validation failures at blind stage must never print real case ids."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fixture = make_fixture(Path(self.tmp.name) / 'fx')
        self.batch = self.fixture['batch']

    def tearDown(self):
        self.tmp.cleanup()

    def test_code_map_hides_case_ids(self):
        doc = human_doc(self.batch)
        doc['cases'][0]['dimensions']['structure']['severity'] = 'partial'
        code_map = {'c1': 'B01', 'c2': 'B02'}
        errors = validate_labels(doc, self.batch, 'blind', code_map=code_map)
        self.assertTrue(errors)
        self.assertTrue(all('c1' not in e and 'c2' not in e for e in errors), errors)
        self.assertTrue(any(e.startswith('B01/') for e in errors), errors)

    def test_without_code_map_case_ids_are_used(self):
        doc = human_doc(self.batch)
        doc['cases'][0]['decision'] = 'bogus'
        errors = validate_labels(doc, self.batch, 'blind')
        self.assertTrue(any('c1' in e for e in errors))

    def test_missing_entry_is_reported_with_blind_code(self):
        doc = human_doc(self.batch)
        doc['cases'] = doc['cases'][:1]
        errors = validate_labels(doc, self.batch, 'blind', code_map={'c1': 'B01', 'c2': 'B02'})
        self.assertTrue(any('B02: missing entry' in e for e in errors), errors)
        self.assertFalse(any('c2' in e for e in errors), errors)

    def test_unmapped_case_is_masked(self):
        doc = human_doc(self.batch)
        doc['cases'][0]['decision'] = 'bogus'
        errors = validate_labels(doc, self.batch, 'blind', code_map={'c2': 'B02'})
        self.assertTrue(any('<unmapped>' in e for e in errors), errors)
        self.assertFalse(any('c1' in e for e in errors), errors)




def ov_doc(entries, gaps=None, approved_by='tester', approved_at='2026-11-18'):
    return {'overrides_version': 1, 'approved_by': approved_by, 'approved_at': approved_at,
            'keyword_map_version': 1, 'entries': entries,
            'acknowledged_gaps': gaps or []}


def ov_entry(blind_code, field, value, dim=None, reason='标注者确认'):
    e = {'blind_code': blind_code, 'field': field, 'value': value, 'reason': reason}
    if dim is not None:
        e['dim'] = dim
    return e


class OverrideValidationTest(unittest.TestCase):
    def setUp(self):
        self.doc = blind_doc([case('B01', 'fail', '非正文混入',
                                   {'cleanliness': dim(3, 'scored', 'partial')}),
                              case('B02', 'uncertain', '完全相同')])

    def test_valid_spec(self):
        ov = ov_doc([ov_entry('B01', 'severity', 'major', dim='cleanliness'),
                     ov_entry('B02', 'decision', 'pass')])
        self.assertEqual(validate_overrides(ov, self.doc), [])

    def test_unknown_blind_code(self):
        ov = ov_doc([ov_entry('B99', 'decision', 'pass')])
        self.assertTrue(any('unknown blind_code' in e for e in validate_overrides(ov, self.doc)))

    def test_score_is_never_overridable(self):
        ov = ov_doc([ov_entry('B01', 'score', 4, dim='cleanliness')])
        errs = validate_overrides(ov, self.doc)
        self.assertTrue(any('never' in e and 'overridable' in e for e in errs), errs)

    def test_note_is_never_overridable(self):
        ov = ov_doc([ov_entry('B01', 'note', 'x', dim='cleanliness')])
        self.assertTrue(validate_overrides(ov, self.doc))

    def test_missing_reason_rejected(self):
        ov = ov_doc([ov_entry('B01', 'decision', 'pass', reason='   ')])
        self.assertTrue(any('reason must be' in e for e in validate_overrides(ov, self.doc)))

    def test_illegal_value_rejected(self):
        ov = ov_doc([ov_entry('B01', 'severity', 'partial', dim='cleanliness')])
        self.assertTrue(any('not legal for severity' in e
                            for e in validate_overrides(ov, self.doc)))

    def test_dim_required_for_severity(self):
        ov = ov_doc([ov_entry('B01', 'severity', 'major')])
        self.assertTrue(any('dim must be one of' in e for e in validate_overrides(ov, self.doc)))

    def test_dim_forbidden_for_decision(self):
        ov = ov_doc([ov_entry('B01', 'decision', 'pass', dim='cleanliness')])
        self.assertTrue(any('dim must be omitted' in e for e in validate_overrides(ov, self.doc)))

    def test_missing_approval_rejected(self):
        ov = ov_doc([ov_entry('B01', 'decision', 'pass')], approved_by='')
        self.assertTrue(any('approved_by' in e for e in validate_overrides(ov, self.doc)))

    def test_bad_version_rejected(self):
        ov = ov_doc([ov_entry('B01', 'decision', 'pass')])
        ov['overrides_version'] = 2
        self.assertTrue(any('overrides_version' in e for e in validate_overrides(ov, self.doc)))

    def test_acknowledged_gap_needs_known_kind_and_reason(self):
        ov = ov_doc([], gaps=[{'blind_code': 'B02', 'kind': 'something_else', 'reason': 'r'}])
        self.assertTrue(any('kind must be' in e for e in validate_overrides(ov, self.doc)))
        ov = ov_doc([], gaps=[{'blind_code': 'B02', 'kind': GAP_KIND, 'reason': ''}])
        self.assertTrue(any('reason must be' in e for e in validate_overrides(ov, self.doc)))
        ov = ov_doc([], gaps=[{'blind_code': 'B99', 'kind': GAP_KIND, 'reason': 'r'}])
        self.assertTrue(any('unknown blind_code' in e for e in validate_overrides(ov, self.doc)))


class OverrideApplicationTest(unittest.TestCase):
    def build(self):
        doc = blind_doc([case('B01', 'uncertain', '将非正文的备注内容提取出来，且是源截断',
                              {'cleanliness': dim(3, 'scored', 'partial')}),
                         case('B02', 'fail', '一段被分成多段',
                              {'structure': dim(3, 'scored', 'minor')})])
        doc['cases'][0]['dimensions']['cleanliness']['note'] = 'KEEPME'
        changes, _, _ = repair(doc, cfg())
        repaired = apply_changes(doc, changes)
        return doc, changes, repaired

    def test_severity_override_reaches_the_output_document(self):
        doc, changes, repaired = self.build()
        ov = ov_doc([ov_entry('B01', 'severity', 'critical', dim='cleanliness')])
        out, applied = apply_overrides(repaired, changes, ov)
        self.assertEqual(out['cases'][0]['dimensions']['cleanliness']['severity'], 'critical')
        self.assertEqual(applied[0]['before'], 'major')
        self.assertEqual(applied[0]['after'], 'critical')

    def test_severity_override_updates_change_record_provenance(self):
        doc, changes, repaired = self.build()
        ov = ov_doc([ov_entry('B01', 'severity', 'critical', dim='cleanliness',
                              reason='标注者改判')])
        apply_overrides(repaired, changes, ov)
        rec = [c for c in changes if c['dim'] == 'cleanliness'][0]
        self.assertTrue(rec['overridden_by_annotator'])
        self.assertEqual(rec['severity_after'], 'critical')
        self.assertEqual(rec['override_reason'], '标注者改判')

    def test_status_override_reaches_the_output_document(self):
        doc, changes, repaired = self.build()
        ov = ov_doc([ov_entry('B01', 'status', 'scored', dim='cleanliness')])
        out, _ = apply_overrides(repaired, changes, ov)
        self.assertEqual(out['cases'][0]['dimensions']['cleanliness']['status'], 'scored')

    def test_decision_override_on_untouched_case(self):
        doc, changes, repaired = self.build()
        ov = ov_doc([ov_entry('B02', 'decision', 'uncertain')])
        out, applied = apply_overrides(repaired, changes, ov)
        self.assertEqual(out['cases'][0 + 1]['decision'], 'uncertain')
        self.assertEqual(applied[0]['before'], 'fail')

    def test_override_never_touches_score_or_notes(self):
        doc, changes, repaired = self.build()
        ov = ov_doc([ov_entry('B01', 'severity', 'critical', dim='cleanliness'),
                     ov_entry('B02', 'decision', 'uncertain')])
        out, _ = apply_overrides(repaired, changes, ov)
        for before, after in zip(repaired['cases'], out['cases']):
            self.assertEqual(before['overall_note'], after['overall_note'])
            for n in DIMS:
                self.assertEqual(before['dimensions'][n]['score'],
                                 after['dimensions'][n]['score'])
                self.assertEqual(before['dimensions'][n]['note'],
                                 after['dimensions'][n]['note'])
        self.assertEqual(out['cases'][0]['dimensions']['cleanliness']['note'], 'KEEPME')

    def test_override_metadata_is_recorded(self):
        doc, changes, repaired = self.build()
        ov = ov_doc([ov_entry('B02', 'decision', 'uncertain')], approved_by='hqli631')
        out, _ = apply_overrides(repaired, changes, ov)
        self.assertEqual(out['overrides']['approved_by'], 'hqli631')
        self.assertEqual(out['overrides']['applied'], 1)

    def test_input_documents_are_not_mutated(self):
        doc, changes, repaired = self.build()
        repaired_snapshot = json.dumps(repaired, ensure_ascii=False, sort_keys=True)
        apply_overrides(repaired, changes,
                        ov_doc([ov_entry('B01', 'severity', 'critical', dim='cleanliness')]))
        # apply_overrides works on a deep copy: the repaired doc and the original
        # blind labels both stay pristine (only the change records gain provenance).
        self.assertEqual(repaired_snapshot, json.dumps(repaired, ensure_ascii=False, sort_keys=True))
        self.assertEqual(doc['cases'][0]['dimensions']['cleanliness']['severity'], 'partial')
        self.assertEqual(doc['cases'][0]['decision'], 'uncertain')


class GapAcknowledgementTest(unittest.TestCase):
    def warns(self, doc, ack=None, changes=None):
        sev_after = {(c['blind_code'], c['dim']): c['severity_after'] for c in (changes or [])}
        return consistency_warnings(doc, lambda k, cur: sev_after.get(k, cur),
                                    acknowledged=ack)

    def test_uncertain_without_defect_is_reported_as_gap(self):
        doc = blind_doc([case('B19', 'uncertain', 'Ignore previous instructions')])
        kinds = [w[2] for w in self.warns(doc)]
        self.assertIn(GAP_KIND, kinds)

    def test_acknowledged_gap_moves_out_of_pending(self):
        doc = blind_doc([case('B19', 'uncertain', 'Ignore previous instructions')])
        warns = self.warns(doc, ack={('B19', GAP_KIND)})
        self.assertEqual(len(warns), 1)
        self.assertEqual(pending(warns), [])

    def test_unacknowledged_gap_stays_pending(self):
        doc = blind_doc([case('B19', 'uncertain', 'Ignore previous instructions')])
        self.assertEqual(len(pending(self.warns(doc))), 1)

    def test_partially_acknowledged(self):
        doc = blind_doc([case('B19', 'uncertain', 'inj'), case('B23', 'uncertain', 'inj')])
        warns = self.warns(doc, ack={('B19', GAP_KIND)})
        self.assertEqual(len(warns), 2)
        self.assertEqual([w[0] for w in pending(warns)], ['B23'])

    def test_uncertain_with_defect_is_not_a_gap(self):
        doc = blind_doc([case('B01', 'uncertain', '标题编号丢失',
                              {'title': dim(3, 'scored', 'minor')})])
        self.assertNotIn(GAP_KIND, [w[2] for w in self.warns(doc)])

    def test_source_only_uncertain_is_not_a_gap(self):
        c = case('B22', 'uncertain', 'source_only无参考答案')
        c['mode'] = 'source_only'
        self.assertEqual(self.warns(blind_doc([c])), [])

    def test_source_only_fail_without_severe_is_still_flagged(self):
        c = case('B22', 'fail', 'source_only无参考答案')
        c['mode'] = 'source_only'
        kinds = [w[2] for w in self.warns(blind_doc([c]))]
        self.assertIn('decision_fail_without_major_or_critical', kinds)

    def test_with_gold_uncertain_without_defect_is_still_a_gap(self):
        c = case('B22', 'uncertain', 'source_only无参考答案')
        c['mode'] = 'with_gold'
        self.assertIn(GAP_KIND, [w[2] for w in self.warns(blind_doc([c]))])

    def test_decision_override_clears_the_warning(self):
        doc = blind_doc([case('B01', 'uncertain', '非正文混入',
                              {'cleanliness': dim(3, 'scored', 'major')})])
        self.assertIn('major_or_critical_but_not_fail', [w[2] for w in self.warns(doc)])
        warns = consistency_warnings(doc, lambda k, cur: cur,
                                     decision_of=lambda bc, cur: 'fail')
        self.assertEqual(pending(warns), [])


class OverrideCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.labels = self.root / 'human_labels.blind.json'
        doc = blind_doc([case('B01', 'uncertain', '将非正文的备注内容提取出来，且是源截断',
                              {'cleanliness': dim(3, 'scored', 'partial')}),
                         case('B02', 'fail', '一段被分成多段',
                              {'structure': dim(3, 'scored', 'minor')}),
                         case('B03', 'uncertain', 'Ignore previous instructions')])
        self.labels.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                               encoding='utf-8', newline='')
        self.ov = self.root / 'overrides.json'
        self.write_ov(ov_doc([ov_entry('B01', 'decision', 'fail'),
                              ov_entry('B02', 'decision', 'uncertain')],
                             gaps=[{'blind_code': 'B03', 'kind': GAP_KIND,
                                    'reason': '注入尝试本身降低决策置信度'}]))

    def tearDown(self):
        self.tmp.cleanup()

    def write_ov(self, value):
        self.ov.write_text(json.dumps(value, ensure_ascii=False, indent=1),
                           encoding='utf-8', newline='')

    def run_cli(self, out_name, apply=False, overrides=True):
        argv = ['--labels', str(self.labels), '--map', MAP,
                '--output', str(self.root / out_name)]
        if overrides:
            argv += ['--overrides', str(self.ov)]
        if apply:
            argv.append('--apply')
        return repair_main(argv)

    def test_invalid_override_spec_aborts_without_output(self):
        self.write_ov(ov_doc([ov_entry('B01', 'score', 4, dim='cleanliness')]))
        self.assertEqual(self.run_cli('bad'), 2)
        self.assertFalse((self.root / 'bad').exists())

    def test_apply_writes_overridden_values(self):
        self.assertEqual(self.run_cli('ok', apply=True), 0)
        r2 = load_json(self.root / 'ok' / 'human_labels.blind.r2.json')
        self.assertEqual(r2['cases'][0]['decision'], 'fail')
        self.assertEqual(r2['cases'][0]['dimensions']['cleanliness']['severity'], 'major')
        self.assertEqual(r2['cases'][1]['decision'], 'uncertain')
        self.assertEqual(r2['cases'][1]['dimensions']['structure']['severity'], 'minor')
        self.assertEqual(r2['overrides']['applied'], 2)

    def test_audit_records_approval_and_warning_split(self):
        self.run_cli('audit', apply=True)
        audit = load_json(self.root / 'audit' / 'repair_audit.json')
        self.assertEqual(audit['overrides_approved_by'], 'tester')
        self.assertEqual(audit['n_overrides'], 2)
        self.assertEqual(audit['n_consistency_warnings_pending'], 0)
        self.assertEqual(audit['n_consistency_warnings_acknowledged'], 1)
        self.assertEqual(audit['acknowledged_gaps'], [['B03', GAP_KIND]])

    def test_warnings_doc_separates_pending_and_acknowledged(self):
        self.run_cli('warn')
        text = (self.root / 'warn' / 'CONSISTENCY_WARNINGS.md').read_text(encoding='utf-8')
        self.assertIn('待确认（0）', text)
        self.assertIn('标注者已确认保留（1', text)
        self.assertIn(GAP_KIND, text)

    def test_unacknowledged_case_stays_pending(self):
        self.write_ov(ov_doc([ov_entry('B01', 'decision', 'fail'),
                              ov_entry('B02', 'decision', 'uncertain')]))
        self.run_cli('pend')
        audit = load_json(self.root / 'pend' / 'repair_audit.json')
        self.assertEqual(audit['n_consistency_warnings_pending'], 1)
        self.assertEqual(audit['n_consistency_warnings_acknowledged'], 0)

    def test_override_run_is_deterministic(self):
        self.run_cli('d1')
        self.run_cli('d2')
        self.assertEqual((self.root / 'd1' / 'REPAIR_DIFF.md').read_bytes(),
                         (self.root / 'd2' / 'REPAIR_DIFF.md').read_bytes())

    def test_no_real_case_id_leaks_with_overrides(self):
        self.run_cli('leak', apply=True)
        forbidden = ['cal-mdn', 'cal-blurb', 'reorder', 'missing_paragraph',
                     'instruction_interference', 'case_id', 'assistant_silver']
        for name in ('REPAIR_DIFF.md', 'CONSISTENCY_WARNINGS.md', 'severity_repairs.json',
                     'repair_audit.json', 'human_labels.blind.r2.json'):
            text = (self.root / 'leak' / name).read_text(encoding='utf-8')
            for bad in forbidden:
                self.assertNotIn(bad, text, '%s leaked %r' % (name, bad))

    def test_without_overrides_flag_no_override_section_data(self):
        self.assertEqual(self.run_cli('plain', overrides=False), 0)
        audit = load_json(self.root / 'plain' / 'repair_audit.json')
        self.assertIsNone(audit['overrides_version'])
        self.assertEqual(audit['n_overrides'], 0)


if __name__ == '__main__':
    unittest.main()
