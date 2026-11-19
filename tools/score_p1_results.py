"""P1 acceptance + descriptive scoring (pre-registered docs/P1_META_EVAL_PLAN.md).

Development-only acceptance against P0 final human gold (human_gold.final.json):
  reject rate < 10%, severe_miss <= 1, accepted decision mismatches <= 1.
Reuses ingest_human_labels.compare_human_case/aggregate_human so metric semantics
are identical to P0. Cross-judge agreement and probe stability are DESCRIPTIVE
ONLY (no acceptance thresholds). frozen_test is never scored here. check_freeze
validates the dev batch against freeze v3 (full frozen manifest, subset cases).
Zero model calls. Output refuses overwrite (exit 3).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.ingest_human_labels import compare_human_case, aggregate_human
from tools.score_judge_results import check_freeze, sha256_bytes
from src.webextractor.rubrics_v2 import DIMENSIONS

ROOT = Path(__file__).resolve().parents[1]
THRESHOLDS = {'reject_rate_lt': 0.10, 'severe_miss_le': 1, 'decision_mismatch_le': 1}


def _load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _gold_map(gold):
    cases = gold['cases'] if isinstance(gold, dict) else gold
    if isinstance(cases, dict):
        cases = list(cases.values())
    return {c['case_id']: c for c in cases}


def _silver(silver_dir, cid):
    p = Path(silver_dir) / (cid + '.label.json')
    return _load(p) if p.exists() else None


def _rows(batch, gold_map, silver_dir):
    out = []
    for row in batch['cases']:
        cid = row['case_id']
        entry = gold_map.get(cid)
        if entry is None:
            raise ValueError('No human gold for case: ' + cid)
        r, _reasons = compare_human_case(row, entry, _silver(silver_dir, cid))
        out.append(r)
    return out


def _acceptance(rows, agg):
    n = agg['n_cases']
    rejected = agg['rejected']
    reject_rate = round(rejected / n, 4) if n else None
    severe_miss = len(agg.get('severe_miss_cases', []))
    mismatches = sum(1 for r in rows if r['judge_status'] == 'accepted' and not r.get('decision_match'))
    checks = {'reject_rate_lt_0.10': reject_rate is not None and reject_rate < THRESHOLDS['reject_rate_lt'],
              'severe_miss_le_1': severe_miss <= THRESHOLDS['severe_miss_le'],
              'decision_mismatch_le_1': mismatches <= THRESHOLDS['decision_mismatch_le']}
    return {'n_cases': n, 'accepted': agg['accepted'], 'rejected': rejected,
            'reject_rate': reject_rate, 'severe_miss_count': severe_miss,
            'severe_miss_cases': agg.get('severe_miss_cases', []),
            'false_alarm_cases': agg.get('false_alarm_cases', []),
            'accepted_decision_mismatches': mismatches,
            'thresholds': THRESHOLDS, 'checks': checks,
            'verdict': 'ACCEPT' if all(checks.values()) else 'REJECT'}


def _cross_judge(batch, cross, silver_dir):
    if cross is None:
        return None
    b1 = {r['case_id']: r for r in batch['cases']}
    rows = []
    for row2 in cross['cases']:
        cid = row2['case_id']
        row1 = b1.get(cid)
        if row1 is None:
            continue
        rep1, rep2 = row1.get('report') or {}, row2.get('report') or {}
        if rep1.get('status') != 'accepted' or rep2.get('status') != 'accepted':
            rows.append({'case_id': cid, 'judge_status': 'rejected_pair',
                         'judge1_status': rep1.get('status'), 'judge2_status': rep2.get('status')})
            continue
        a2 = rep2['assessment']
        entry2 = {'decision': a2['decision'], 'dimensions': a2['dimensions']}
        r, _ = compare_human_case(row1, entry2, _silver(silver_dir, cid))
        r['case_id'] = cid
        rows.append(r)
    accepted = [r for r in rows if r.get('judge_status') == 'accepted']
    agg = aggregate_human(accepted) if accepted else {}
    rej2 = sum(1 for r in cross['cases'] if (r.get('report') or {}).get('status') != 'accepted')
    return {'model2': cross.get('signature', {}).get('model'),
            'n_cases': len(cross['cases']), 'judge2_rejected': rej2,
            'both_accepted': len(accepted), 'agreement': agg,
            'note': 'judge1 vs judge2 agreement; descriptive only, not accuracy.'}


def _probe_stability(batch, probe):
    if probe is None:
        return None
    base = {r['case_id']: r for r in batch['cases']}
    n = flips = exact = sign = comp = 0
    per = []
    for row in probe['cases']:
        cid = row['case_id']
        b = base.get(cid)
        rp, rb = row.get('report') or {}, (b or {}).get('report') or {}
        if rp.get('status') != 'accepted' or rb.get('status') != 'accepted':
            per.append({'case_id': cid, 'comparable': False,
                        'probe_status': rp.get('status'), 'base_status': rb.get('status')})
            continue
        ap, ab = rp['assessment'], rb['assessment']
        flip = ap['decision'] != ab['decision']
        de = ds = dc = 0
        for d in DIMENSIONS:
            jp, jb = ap['dimensions'].get(d) or {}, ab['dimensions'].get(d) or {}
            sp, sb = jp.get('score'), jb.get('score')
            if type(sp) is int and type(sb) is int:
                dc += 1
                de += int(sp == sb)
                ds += int((jp.get('severity') == 'none') == (jb.get('severity') == 'none'))
        n += 1; flips += int(flip); exact += de; sign += ds; comp += dc
        per.append({'case_id': cid, 'comparable': True, 'decision_flip': flip,
                    'base_decision': ab['decision'], 'probe_decision': ap['decision'],
                    'dim_exact': (de / dc) if dc else None})
    return {'probe_key': probe.get('probe_key'), 'n_comparable_cases': n,
            'decision_flip_rate': round(flips / n, 4) if n else None,
            'dim_exact_rate': round(exact / comp, 4) if comp else None,
            'severity_sign_rate': round(sign / comp, 4) if comp else None,
            'per_case': per, 'note': 'descriptive stability vs production baseline; not acceptance.'}


def main(argv=None):
    ap = argparse.ArgumentParser(description='P1 dev-only acceptance + descriptive metrics.')
    ap.add_argument('--batch', type=Path, required=True, help='v1.1 development batch report')
    ap.add_argument('--gold', type=Path, default=ROOT / 'outputs/human_review/final.v1/human_gold.final.json')
    ap.add_argument('--silver-dir', type=Path, default=ROOT / 'samples/calibration/labels')
    ap.add_argument('--cross', type=Path, default=None)
    ap.add_argument('--probe-position', type=Path, default=None)
    ap.add_argument('--probe-phrasing', type=Path, default=None)
    ap.add_argument('--probe-stability', type=Path, default=None)
    ap.add_argument('--freeze', type=Path, default=ROOT / 'outputs/rubrics_judge.node3.freeze.v3.json')
    ap.add_argument('--manifest', type=Path, default=ROOT / 'samples/calibration_manifest.json')
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--md', type=Path, default=None)
    args = ap.parse_args(argv)
    if args.output.exists() or (args.md and args.md.exists()):
        print('Output exists; choose a new filename.', file=sys.stderr)
        return 3
    batch = _load(args.batch)
    if batch.get('split_filter') not in (None, 'development'):
        print('P1 acceptance requires a development-only batch.', file=sys.stderr)
        return 2
    if any(r['split'] != 'development' for r in batch['cases']):
        print('Batch contains non-development cases; P1 acceptance is dev-only.', file=sys.stderr)
        return 2
    gold_map = _gold_map(_load(args.gold))
    rows = _rows(batch, gold_map, args.silver_dir)
    agg = aggregate_human(rows)
    acceptance = _acceptance(rows, agg)
    cross = _cross_judge(batch, _load(args.cross) if args.cross else None, args.silver_dir)
    probes = {'position': _probe_stability(batch, _load(args.probe_position) if args.probe_position else None),
              'phrasing': _probe_stability(batch, _load(args.probe_phrasing) if args.probe_phrasing else None),
              'stability': _probe_stability(batch, _load(args.probe_stability) if args.probe_stability else None)}
    freeze = _load(args.freeze)
    stability_arg = _load(args.probe_stability) if args.probe_stability else {'cases': []}
    problems = check_freeze(batch, stability_arg, freeze, manifest_path=str(args.manifest))
    result = {'tool': 'score_p1_results.py', 'scope': 'development_only',
              'acceptance': acceptance, 'dev_metrics': agg,
              'cross_judge': cross, 'probes': probes,
              'freeze_check': problems if problems else 'NONE',
              'inputs': {'batch_manifest_sha256': batch.get('manifest_sha256'),
                         'batch_signature': batch.get('signature'),
                         'gold_sha256': sha256_bytes(Path(args.gold).read_bytes()),
                         'freeze_version': freeze.get('freeze_version'),
                         'freeze_judge_sha256': freeze.get('files', {}).get('src/webextractor/rubrics_judge.py')},
              'limitations': ['single annotator, no IAA', 'agreement is not accuracy',
                              'dev only; frozen_test sealed and not re-run',
                              'post-adjudication human gold; independent anchor is P0 blind 0.75/kappa0.5077',
                              'cross-judge is same-family second model; self-preference coverage limited',
                              'probes descriptive only; judge scores are not training reward']}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='')
    if args.md:
        a = acceptance
        lines = ['# P1 development acceptance (descriptive cross-judge/probes)', '',
                 '- verdict: **%s**' % a['verdict'],
                 '- reject rate: %s (<0.10 required); rejected %d/%d' % (a['reject_rate'], a['rejected'], a['n_cases']),
                 '- severe_miss: %d (<=1 required); cases %s' % (a['severe_miss_count'], a['severe_miss_cases']),
                 '- accepted decision mismatches: %d (<=1 required)' % a['accepted_decision_mismatches'],
                 '- decision match / kappa: %s / %s' % (agg.get('decision_match_rate'), agg.get('decision_cohen_kappa')),
                 '- dim exact / within1: %s / %s; severity sign: %s' % (agg.get('dim_exact_rate'), agg.get('dim_within1_rate'), agg.get('severity_sign_rate')),
                 '- false_alarm: %s' % agg.get('false_alarm_cases'),
                 '- freeze check: %s' % (problems if problems else 'NONE'), '',
                 'Thresholds pre-registered in docs/P1_META_EVAL_PLAN.md. Dev-only; frozen_test sealed.',
                 'Agreement is not accuracy; single annotator; judge scores are not training reward.']
        if cross:
            lines += ['', '## Cross-judge (descriptive)', '- model2: %s; both accepted: %d; judge2 rejected: %d' % (cross['model2'], cross['both_accepted'], cross['judge2_rejected']),
                      '- agreement: %s' % json.dumps(cross['agreement'], ensure_ascii=False)]
        for k, v in probes.items():
            if v:
                lines += ['', '## Probe %s (descriptive)' % k,
                          '- comparable cases: %s; decision flip rate: %s; dim exact: %s' % (v['n_comparable_cases'], v['decision_flip_rate'], v['dim_exact_rate'])]
        args.md.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='')
    print(json.dumps({'output': str(args.output), 'verdict': acceptance['verdict'],
                      'reject_rate': acceptance['reject_rate'], 'severe_miss': acceptance['severe_miss_count'],
                      'decision_mismatches': acceptance['accepted_decision_mismatches'],
                      'freeze_check': problems if problems else 'NONE'}, ensure_ascii=False))
    return 0 if acceptance['verdict'] == 'ACCEPT' else 2


if __name__ == '__main__':
    raise SystemExit(main())
