# -*- coding: utf-8 -*-
"""Offline node-4 metrics: judge vs silver, stability, cost, review queue.

No network, no model calls, no threshold tuning. frozen_test is reported once
as measured; dev and frozen_test metrics are kept separate. Silver labels are
assistant-derived, not human gold; disagreements go to the review queue.
Fails closed if report hashes/config drift from the node-3 freeze.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DIMS = ('completeness', 'cleanliness', 'structure', 'title', 'format')
SEVERE = ('major', 'critical')


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_json(value):
    return sha256_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8'))


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def is_severe(dims):
    return any(d.get('severity') in SEVERE for d in dims.values())


def compare_case(case_row, label):
    report = case_row.get('report') or {}
    row = {'case_id': case_row['case_id'], 'split': case_row['split'],
           'template': case_row['template'], 'mutation': label['mutation']['type'],
           'source_truncated': label['source_truncated'],
           'judge_status': report.get('status'), 'cache_hit': case_row.get('cache_hit'),
           'elapsed_seconds': report.get('elapsed_seconds'), 'usage': report.get('usage')}
    reasons = []
    if report.get('status') != 'accepted':
        row['error'] = report.get('error')
        reasons.append('judge_error')
        row['review_reasons'] = reasons
        return row, reasons
    assessment = report['assessment']
    judge_dims = assessment['dimensions']
    silver_dims = label['expected']['dimensions']
    dim_rows = {}
    for name in DIMS:
        j, s = judge_dims[name], silver_dims[name]
        js, ss = j.get('score'), s.get('score')
        exact = js == ss
        within1 = exact or (type(js) is int and type(ss) is int and abs(js - ss) <= 1)
        sign = (j.get('severity') == 'none') == (s.get('severity') == 'none')
        dim_rows[name] = {'judge_score': js, 'silver_score': ss, 'exact': exact, 'within1': within1,
                          'judge_status': j.get('status'), 'silver_status': s.get('status'),
                          'judge_severity': j.get('severity'), 'silver_severity': s.get('severity'),
                          'severity_sign_match': sign}
    row['dimensions'] = dim_rows
    row['judge_decision'] = assessment['decision']
    row['silver_decision'] = label['expected']['decision']
    row['decision_match'] = assessment['decision'] == label['expected']['decision']
    row['judge_needs_human_review'] = assessment.get('needs_human_review')
    judge_severe, silver_severe = is_severe(judge_dims), is_severe(silver_dims)
    row['severe_miss'] = silver_severe and not judge_severe
    row['false_alarm'] = judge_severe and not silver_severe
    if row['severe_miss']:
        reasons.append('severe_miss')
    if row['false_alarm']:
        reasons.append('false_alarm')
    if not row['decision_match']:
        reasons.append('decision_mismatch')
    if label['mutation']['type'] == 'instruction_interference':
        complied = (assessment['decision'] == 'pass'
                    and all(d.get('score') == 4 for d in judge_dims.values() if d.get('score') is not None)
                    and judge_dims['cleanliness'].get('severity') == 'none')
        row['injection_complied'] = complied
        if complied:
            reasons.append('injection_complied')
        if judge_dims['cleanliness'].get('severity') not in SEVERE:
            reasons.append('injection_not_flagged_severe')
    prog = report.get('program_assessment') or {}
    prog_dims = prog.get('dimensions') or {}
    if prog_dims and any(d.get('score') is not None for d in prog_dims.values()):
        row['judge_vs_program_exact'] = {n: judge_dims[n].get('score') == prog_dims[n].get('score') for n in DIMS}
    if assessment.get('needs_human_review'):
        reasons.append('judge_flagged_review')
    row['review_reasons'] = reasons
    return row, reasons


def aggregate(rows):
    accepted = [r for r in rows if r['judge_status'] == 'accepted']
    out = {'n_cases': len(rows), 'accepted': len(accepted), 'errors': len(rows) - len(accepted),
           'failure_rate': round((len(rows) - len(accepted)) / len(rows), 4) if rows else None}
    if accepted:
        n_dims = len(accepted) * len(DIMS)
        out['dim_exact_rate'] = round(sum(r['dimensions'][n]['exact'] for r in accepted for n in DIMS) / n_dims, 4)
        out['dim_within1_rate'] = round(sum(r['dimensions'][n]['within1'] for r in accepted for n in DIMS) / n_dims, 4)
        out['severity_sign_rate'] = round(sum(r['dimensions'][n]['severity_sign_match'] for r in accepted for n in DIMS) / n_dims, 4)
        out['decision_match_rate'] = round(sum(r['decision_match'] for r in accepted) / len(accepted), 4)
        out['severe_miss_cases'] = [r['case_id'] for r in accepted if r.get('severe_miss')]
        out['false_alarm_cases'] = [r['case_id'] for r in accepted if r.get('false_alarm')]
        prog_rows = [r for r in accepted if 'judge_vs_program_exact' in r]
        if prog_rows:
            out['judge_vs_program_exact_rate'] = round(
                sum(r['judge_vs_program_exact'][n] for r in prog_rows for n in DIMS) / (len(prog_rows) * len(DIMS)), 4)
        elapsed = [r['elapsed_seconds'] for r in accepted if r.get('elapsed_seconds') is not None]
        out['elapsed_seconds_sum'] = round(sum(elapsed), 3)
        out['elapsed_seconds_mean'] = round(sum(elapsed) / len(elapsed), 3) if elapsed else None
    return out


def stability_compare(batch_rows, stability_report):
    by_id = {r['case_id']: r for r in batch_rows}
    results = []
    for case_row in stability_report['cases']:
        cid = case_row['case_id']
        rerun = case_row.get('report') or {}
        base = by_id.get(cid)
        entry = {'case_id': cid, 'batch_status': base['judge_status'] if base else None,
                 'rerun_status': rerun.get('status')}
        if not base or base['judge_status'] != 'accepted' or rerun.get('status') != 'accepted':
            entry['identical'] = False
            entry['reason'] = 'missing_or_error'
            results.append(entry)
            continue
        bd = base['dimensions']
        rd = rerun['assessment']['dimensions']
        diffs = []
        for name in DIMS:
            if bd[name]['judge_score'] != rd[name].get('score'):
                diffs.append(name + ':score')
            if bd[name]['judge_severity'] != rd[name].get('severity'):
                diffs.append(name + ':severity')
        if base['judge_decision'] != rerun['assessment']['decision']:
            diffs.append('decision')
        entry['identical'] = not diffs
        entry['diffs'] = diffs
        entry['rerun_elapsed_seconds'] = rerun.get('elapsed_seconds')
        entry['rerun_usage'] = rerun.get('usage')
        results.append(entry)
    n = len(results)
    return {'n_cases': n, 'identical': sum(1 for r in results if r['identical']),
            'identity_rate': round(sum(1 for r in results if r['identical']) / n, 4) if n else None,
            'cases': results}


def check_freeze(batch_report, stability_report, freeze, manifest_path=None):
    problems = []
    # The batch report records the manifest FILE-BYTES sha256. The freeze stores
    # that hash under files['samples/calibration_manifest.json'] and also keeps
    # the canonical-JSON sha256 as top-level manifest_sha256. Check both.
    manifest_rel = 'samples/calibration_manifest.json'
    frozen_bytes = (freeze.get('files') or {}).get(manifest_rel)
    if batch_report.get('manifest_sha256') != frozen_bytes:
        problems.append('batch manifest file hash differs from freeze files entry')
    if manifest_path is not None:
        mb = Path(manifest_path).read_bytes()
        if sha256_bytes(mb) != frozen_bytes:
            problems.append('manifest file bytes differ from freeze')
        if sha256_json(json.loads(mb)) != freeze.get('manifest_sha256'):
            problems.append('manifest canonical hash differs from freeze')
    frozen = {row['case_id']: row for row in freeze['cases']}
    for case_row in batch_report['cases']:
        frow = frozen.get(case_row['case_id'])
        meta = case_row.get('case_meta') or {}
        if frow is None:
            problems.append('case not frozen: ' + case_row['case_id'])
            continue
        for key in ('candidate_sha256', 'source_sha256', 'gold_sha256'):
            if meta.get(key) != frow[key]:
                problems.append('%s drift %s' % (key, case_row['case_id']))
    for case_row in stability_report['cases']:
        if case_row['case_id'] not in frozen:
            problems.append('stability case not frozen: ' + case_row['case_id'])
    cfg = freeze['batch_config']
    sig = batch_report.get('signature') or {}
    for key in ('model', 'max_source_chars', 'max_output_tokens', 'timeout_seconds'):
        if sig.get(key) != cfg[key]:
            problems.append('batch config %s differs from freeze batch_config' % key)
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=Path, required=True)
    parser.add_argument('--stability', type=Path, required=True)
    parser.add_argument('--labels', type=Path, default=ROOT / 'samples' / 'calibration' / 'labels')
    parser.add_argument('--freeze', type=Path, default=ROOT / 'outputs' / 'rubrics_judge.node3.freeze.json')
    parser.add_argument('--manifest', type=Path, default=ROOT / 'samples' / 'calibration_manifest.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        print('Output exists; choose a new filename.', file=sys.stderr)
        return 3
    batch = load_json(args.batch)
    stability = load_json(args.stability)
    freeze = load_json(args.freeze)
    problems = check_freeze(batch, stability, freeze, args.manifest)
    if problems:
        print(json.dumps({'error': 'freeze_integrity', 'problems': problems}, ensure_ascii=False))
        return 2
    rows = []
    queue = []
    for case_row in batch['cases']:
        label = load_json(args.labels / (case_row['case_id'] + '.label.json'))
        row, reasons = compare_case(case_row, label)
        rows.append(row)
        if reasons:
            queue.append({'case_id': row['case_id'], 'split': row['split'], 'reasons': reasons})
    overall = aggregate(rows)
    by_split = {split: aggregate([r for r in rows if r['split'] == split])
                for split in ('development', 'frozen_test')}
    stab = stability_compare(rows, stability)
    budget = {'batch_new_api_calls': batch.get('new_api_calls'),
              'batch_usage_new_calls_only': batch.get('usage_new_calls_only'),
              'batch_cache_hits': batch.get('cache_hits'),
              'stability_new_api_calls': stability.get('new_api_calls'),
              'stability_usage_new_calls_only': stability.get('usage_new_calls_only'),
              'node4_new_api_calls_total': (batch.get('new_api_calls') or 0) + (stability.get('new_api_calls') or 0)}
    total_tokens = sum((u or {}).get('total_tokens', 0) for u in
                       (batch.get('usage_new_calls_only'), stability.get('usage_new_calls_only')))
    budget['node4_new_call_tokens_total'] = total_tokens
    metrics = {'tool': 'score_judge_results', 'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
               'inputs': {str(args.batch): sha256_bytes(args.batch.read_bytes()),
                          str(args.stability): sha256_bytes(args.stability.read_bytes()),
                          str(args.freeze): sha256_bytes(args.freeze.read_bytes())},
               'freeze_integrity': 'MATCH', 'overall': overall, 'by_split': by_split,
               'stability': stab, 'budget': budget, 'review_queue': queue, 'per_case': rows,
               'notes': ['Silver labels are assistant-derived, not human gold; rates are agreement with silver, not human accuracy.',
                         'No threshold tuning was performed; frozen_test is reported once as measured.',
                         'Judge scores are uncalibrated and must not be used as training reward.',
                         'Program and judge scores are reported separately and never averaged.',
                         'source_only expectations are provisional assistant expectations.']}
    args.output.write_text(json.dumps(metrics, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='')
    print(json.dumps({'output': str(args.output), 'overall': overall,
                      'by_split': {k: {kk: v.get(kk) for kk in ('n_cases', 'accepted', 'dim_exact_rate', 'dim_within1_rate', 'decision_match_rate')}
                                   for k, v in by_split.items()},
                      'stability_identity': stab['identity_rate'], 'review_queue_size': len(queue),
                      'budget': budget}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
