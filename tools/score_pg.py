# -*- coding: utf-8 -*-
"""P-G G3 scorer: real-page generalization metrics (post-hoc only).

Mirrors score_pd2.score_run with pg-repair freeze integrity, then reuses the
FROZEN score_pd2._aggregate (classify_pair + bootstrap + generalization metrics +
verdict). Natural pages have no gold: recall_delta only where silver expected
exists; judge classification is the quality evidence. Nothing fed back. Refuses
overwrite.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.score_node5 import classify_pair
from tools.node5_loop import load_json, write_json, sha256_bytes, sha256_json
from tools.run_pg_repair import check_freeze
from tools.score_pd2 import _aggregate, _repaired_from_trace

TOOL_VERSION = '1.0.0'


def score_run(run, freeze, freeze_sha):
    problems = check_freeze(freeze)
    freeze_cases = {c['case_id']: c for c in freeze['cases']}
    per_case, pairs, feedback_rows = [], [], []
    audits = {'checked': 0, 'failures': []}
    integrity = []
    unnecessary = 0
    overrides = []
    for crow in run.get('clusters', []):
        cid = crow['cluster_id']
        for mrow in crow.get('members', []):
            mid = mrow['case_id']
            entry = {'cluster_id': cid, 'case_id': mid, 'status': mrow['status'],
                     'reuse': mrow.get('reuse'), 'baseline_decision': mrow.get('baseline_decision'),
                     'baseline_defect_count': mrow.get('baseline_defect_count'),
                     'trigger_reason': (mrow.get('repair') or {}).get('trigger_reason'),
                     'repair_reference_ids': (mrow.get('repair') or {}).get('reference_ids')}
            audits['checked'] += 1
            fc = freeze_cases.get(mid)
            if fc and mrow.get('source_sha256') != fc['source_sha256']:
                integrity.append({'case_id': mid, 'problem': 'source sha mismatch'})
            if (mrow.get('reuse') or {}).get('generalized_override'):
                overrides.append({'cluster_id': cid, 'case_id': mid})
            for pa in ((mrow.get('repair') or {}).get('prompt_audit') or []):
                if not pa.get('passed'):
                    audits['failures'].append({'case_id': mid, 'problems': ['recorded prompt audit failed'] + pa.get('problems', [])})
            repair = mrow.get('repair') or {}
            if repair.get('triggered'):
                drift = bool((mrow.get('reuse') or {}).get('drift_reasons'))
                if not drift and not mrow.get('baseline_defect_count') and mrow.get('baseline_decision') != 'fail':
                    unnecessary += 1
            critic = mrow.get('critic') or {}
            rejudge = mrow.get('rejudge') or {}
            if mrow.get('status') == 'repaired' and critic.get('status') == 'accepted' and rejudge.get('status') == 'accepted':
                pair = classify_pair(critic['assessment'], rejudge['assessment'])
                entry['pair'] = pair
                pairs.append(pair)
                repaired = _repaired_from_trace(mrow)
                if repaired is None or sha256_json(repaired) != mrow.get('repaired_candidate_sha256'):
                    integrity.append({'case_id': mid, 'problem': 'repaired candidate sha mismatch'})
            entry['baseline_quality'] = mrow.get('baseline_quality')
            entry['repaired_quality'] = mrow.get('repaired_quality')
            bq, rq = mrow.get('baseline_quality'), mrow.get('repaired_quality')
            if bq and rq:
                entry['recall_delta'] = round(rq['block_text_recall'] - bq['block_text_recall'], 6)
            per_case.append(entry)
        fb = crow.get('feedback') or {}
        feedback_rows.append({'cluster_id': cid, 'rep_id': crow.get('rep_id'),
                              'multi_layout': crow.get('multi_layout'), 'layouts': crow.get('layouts'),
                              'shared_rule': crow.get('shared_rule'),
                              'attempted': fb.get('attempted'), 'accepted': fb.get('accepted'),
                              'events': fb.get('events'), 'reuse_recovery': crow.get('reuse_recovery'),
                              'amortization': crow.get('amortization'),
                              'member_rule_cache': crow.get('member_rule_cache')})
    return _aggregate(run, freeze, freeze_sha, problems, per_case, pairs, feedback_rows,
                      audits, integrity, unnecessary, overrides)


def main(argv=None):
    ap = argparse.ArgumentParser(description='P-G G3 real-page generalization scorer (post-hoc).')
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--freeze-path', type=Path, default=ROOT / 'outputs/pg.repair.freeze.v1.json')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args(argv)
    if args.output.exists():
        print('Output exists; choose a new filename.', file=sys.stderr)
        return 3
    run = load_json(args.run)
    freeze = load_json(args.freeze_path)
    freeze_sha = sha256_bytes(args.freeze_path.read_bytes())
    if run.get('freeze_sha256') != freeze_sha:
        print('Run was not produced against this freeze.', file=sys.stderr)
        return 1
    result = score_run(run, freeze, freeze_sha)
    write_json(args.output, result)
    print(json.dumps({'output': str(args.output), 'verdict': result['verdict'],
                      'metrics': result['metrics'], 'success_checks': result['success_checks']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
