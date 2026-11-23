# -*- coding: utf-8 -*-
"""P-G G3 real-page cluster-generalized repair (plan docs/P_G_REAL_TEMPLATE_PLAN.md).

Reuses the P-D2 FROZEN closed loop (run_cluster_pd2 / run_member_pd2 / reuse_pd2 /
validate_feedback / Pd2Guard) on the complete-linkage clusters formed by G2
(suffix-presence). Only the NEW stratum (collected families + variants) enters
critic/repair; the 13 existing snapshots are clustering/reuse-only (plan boundary).
Critic/rejudge v1.4.1 SOURCE_ONLY. Generalized repair sees all cluster sources
(<=8). Feedback validation: structural (unique+ok+nonempty) on every member;
recall-not-worse gate applies ONLY to members with silver expected (variants);
natural pages have NO gold -> judge classification is the only quality evidence
(disclosed). Silver expected = rep extract_html blocks, orchestrator-side only,
never in prompts. Repair <=1 intervention/member. Judge scores NOT training
rewards. Refuses overwrite. --freeze requires approval quote.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.webextractor import rubrics_judge_v141 as j141
from src.webextractor.dom_similarity import structural_features
from tools.node5_loop import sha256_bytes, sha256_json, load_json, write_json
from tools.run_rubrics_judge import _build_provider
from tools.run_pd2_generalize import run_cluster_pd2, Pd2Guard

TOOL_VERSION = '1.0.0'
PLAN_REL = 'docs/P_G_REAL_TEMPLATE_PLAN.md'
CORPUS_REL = 'samples/pg_corpus.v1.json'
CLUSTER_REL = 'outputs/pg.cluster.v1.json'
FREEZE_REL = 'outputs/pg.repair.freeze.v1.json'
PARAMS = {'feature_mode': 'suffix-presence', 'drift_threshold': 0.7}
MODULE_PINS = {'judge_module_sha256': 'src/webextractor/rubrics_judge_v141.py',
               'v14_module_sha256': 'src/webextractor/rubrics_judge_v14.py',
               'rubrics_sha256': 'src/webextractor/rubrics_v2.py',
               'rule_agent_sha256': 'src/webextractor/rule_agent.py',
               'rule_cache_sha256': 'src/webextractor/rule_cache.py'}


def load_pg_pages(corpus_rel=CORPUS_REL):
    manifest = load_json(ROOT / corpus_rel)
    pages = {}
    for p in manifest['pages']:
        sb = (ROOT / 'samples' / p['html']).read_bytes()
        expected = load_json(ROOT / 'samples' / p['silver_expected']) if p.get('silver_expected') else None
        pages[p['id']] = {'id': p['id'], 'manual_group': p['manual_group'],
                          'layout': p.get('layout', 'natural'), 'source': sb,
                          'source_sha256': sha256_bytes(sb), 'html': p['html'],
                          'expected': expected,
                          'features': structural_features(sb, PARAMS['feature_mode'])}
    return pages, manifest


def load_clusters(cluster_rel=CLUSTER_REL):
    res = load_json(ROOT / cluster_rel)
    clusters = {}
    for ci, members in enumerate(res['strata']['new']['complete_linkage']['clusters']):
        cid = 'pg-c%d' % ci
        clusters[cid] = {'rep': members[0], 'members': sorted(members), 'ref_ids': sorted(members)}
    return clusters


def make_freeze(approval_quote, cap=400000, corpus_rel=CORPUS_REL, cluster_rel=CLUSTER_REL):
    if not isinstance(approval_quote, str) or not approval_quote.strip():
        raise ValueError('--approval-quote must record the user approval text')
    pages, manifest = load_pg_pages(corpus_rel)
    clusters = load_clusters(cluster_rel)
    cases = [{'case_id': p['id'], 'html': p['html'], 'source_sha256': p['sha256'],
              'manual_group': p['manual_group'], 'source_kind': p['source_kind']}
             for p in manifest['pages']]
    return {'freeze_version': 'pg-repair-1',
            'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'approval': {'by': 'hqli631', 'quote': approval_quote},
            'preregistration': PLAN_REL, 'plan_sha256': sha256_bytes((ROOT / PLAN_REL).read_bytes()),
            'corpus': corpus_rel, 'corpus_sha256': sha256_bytes((ROOT / corpus_rel).read_bytes()),
            'cluster_file': cluster_rel, 'cluster_sha256': sha256_bytes((ROOT / cluster_rel).read_bytes()),
            'clusters': clusters, 'cases': cases, 'params': PARAMS,
            'protocol': {'model': 'qwen3.8-27b', 'judge_version': j141.JUDGE_VERSION,
                         'base_judge_version': '1.2.0', 'rubrics_version': '2.0.0',
                         'base_source_sha256': j141.BASE_SOURCE_SHA256,
                         **{k: sha256_bytes((ROOT / rel).read_bytes()) for k, rel in MODULE_PINS.items()},
                         'max_source_chars': 20000, 'max_output_tokens': 2200, 'timeout_seconds': 90,
                         'rule_max_attempts': 2, 'evidence_chars': 16000, 'rule_max_output_tokens': 1024,
                         'execution_timeout': 5.0, 'total_timeout': 120.0, 'critic_mode': 'source_only',
                         'generalized_repair': 'reference_pages = all cluster sources (<=8); one shared rule executable nonempty on every reference',
                         'generalized_reuse_semantics': 'feedback-validated generalized rule: fingerprint_drift alone does not invalidate; rule_failure still triggers',
                         'feedback_recall_gate': 'recall-not-worse applies ONLY to members with silver expected (variants); natural pages structural-only (no gold)'},
            'trigger_rule': 'repair iff drift_reasons non-empty OR critic decision==fail OR defects non-empty (P-D frozen)',
            'classification': 'node5 frozen classify_pair (improved/regressed/no_effect/other_change; regressed priority)',
            'feedback_rule': 'improved AND rule unique+ok+nonempty on rep+every member AND recall not worse where silver expected exists; INLINE update on accept',
            'success_criteria': {'multi_layout_feedback_accepted_ge': 1, 'reuse_recovery_after_feedback_ge': 1,
                                 'improvement_rate_ge': 1 / 3, 'regression_rate_le': 0.10,
                                 'leakage_audit_all_passed': True, 'unnecessary_repair_zero': True,
                                 'verdict_labels': ['REAL_TEMPLATE_SIGNAL', 'NO_REAL_TEMPLATE_SIGNAL'],
                                 'note': 'descriptive signal, NOT a reward gate; small real n; natural pages no gold'},
            'budget': {'token_cap': cap, 'max_calls': 30, 'reserve_judge': 16000, 'reserve_rule': 8000},
            'seed': 20261119, 'B': 10000,
            'discipline': ['new stratum only; existing 13 snapshots clustering/reuse-only',
                           'G2 hard-check FAIL (LSH recall) disclosed; CL clusters valid (precision 1.0); no tuning',
                           'critic source_only; silver expected orchestrator-side only; never in prompts',
                           'repair <=1 intervention/member; no tuning; negative results honest',
                           'judge scores NOT training rewards', 'cluster purity != accuracy']}


def check_freeze(freeze, corpus_rel=CORPUS_REL, cluster_rel=CLUSTER_REL):
    problems = []
    if freeze.get('freeze_version') != 'pg-repair-1':
        problems.append('not a pg-repair-1 freeze')
    p = freeze.get('protocol') or {}
    for key, rel in MODULE_PINS.items():
        if p.get(key) != sha256_bytes((ROOT / rel).read_bytes()):
            problems.append('protocol sha drift: ' + rel)
    if p.get('base_source_sha256') != j141.BASE_SOURCE_SHA256:
        problems.append('v1.2 base sha drift')
    if p.get('judge_version') != j141.JUDGE_VERSION:
        problems.append('judge version drift')
    if freeze.get('plan_sha256') != sha256_bytes((ROOT / PLAN_REL).read_bytes()):
        problems.append('plan drift')
    if freeze.get('corpus_sha256') != sha256_bytes((ROOT / corpus_rel).read_bytes()):
        problems.append('corpus drift')
    if freeze.get('cluster_sha256') != sha256_bytes((ROOT / cluster_rel).read_bytes()):
        problems.append('cluster file drift')
    pages, _ = load_pg_pages(corpus_rel)
    for row in freeze.get('cases', []):
        pg = pages.get(row['case_id'])
        if pg is None or pg['source_sha256'] != row['source_sha256']:
            problems.append('source drift ' + row['case_id'])
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description='P-G G3 real-page generalized repair (freeze required).')
    ap.add_argument('--freeze', action='store_true')
    ap.add_argument('--approval-quote', default=None)
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--freeze-path', type=Path, default=ROOT / FREEZE_REL)
    ap.add_argument('--corpus', type=Path, default=ROOT / CORPUS_REL)
    ap.add_argument('--cluster-file', type=Path, default=ROOT / CLUSTER_REL)
    ap.add_argument('--output', type=Path, default=None)
    ap.add_argument('--only', default=None)
    ap.add_argument('--model', default='qwen3.8-27b')
    ap.add_argument('--token-cap', type=int, default=None)
    args = ap.parse_args(argv)
    corpus_rel = str(args.corpus.relative_to(ROOT)) if args.corpus.is_absolute() else str(args.corpus)
    cluster_rel = str(args.cluster_file.relative_to(ROOT)) if args.cluster_file.is_absolute() else str(args.cluster_file)
    if args.freeze:
        if args.freeze_path.exists():
            print('Refusing to overwrite existing freeze.', file=sys.stderr)
            return 3
        try:
            fz = make_freeze(args.approval_quote, corpus_rel=corpus_rel, cluster_rel=cluster_rel)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 1
        write_json(args.freeze_path, fz)
        print(json.dumps({'freeze': str(args.freeze_path), 'cases': len(fz['cases']),
                          'clusters': len(fz['clusters']), 'token_cap': fz['budget']['token_cap'],
                          'max_calls': fz['budget']['max_calls']}, ensure_ascii=False))
        return 0
    if not args.run or args.output is None:
        print('Use --freeze or --run --output PATH', file=sys.stderr)
        return 1
    if args.output.exists():
        print('Output exists; choose a new filename.', file=sys.stderr)
        return 3
    if not args.freeze_path.exists():
        print('Freeze not found; run --freeze first.', file=sys.stderr)
        return 1
    freeze = load_json(args.freeze_path)
    problems = check_freeze(freeze, corpus_rel, cluster_rel)
    if problems:
        for pr in problems:
            print('FREEZE: ' + pr, file=sys.stderr)
        return 1
    if args.model != freeze['protocol'].get('model'):
        print('Model drift: freeze pins ' + str(freeze['protocol'].get('model')), file=sys.stderr)
        return 1
    cap = freeze['budget']['token_cap'] if args.token_cap is None else args.token_cap
    if cap <= 0 or cap > freeze['budget']['token_cap']:
        print('Invalid --token-cap (positive and <= freeze cap).', file=sys.stderr)
        return 1
    provider = _build_provider(args.model, freeze['protocol']['timeout_seconds'])
    rule_provider = _build_provider(args.model, freeze['protocol']['total_timeout'])
    guard = Pd2Guard(cap, freeze['budget']['max_calls'], freeze['budget']['reserve_judge'], freeze['budget']['reserve_rule'])
    pages, _ = load_pg_pages(corpus_rel)
    clusters = freeze['clusters']
    if args.only:
        target = None
        for cid, cinfo in clusters.items():
            if args.only in cinfo['members']:
                target = (cid, {'rep': cinfo['rep'], 'members': [args.only], 'ref_ids': cinfo['ref_ids']})
                break
        if target is None:
            print('Unknown member: ' + args.only, file=sys.stderr)
            return 1
        clusters = {target[0]: target[1]}
    cluster_rows = []
    for cid, cinfo in clusters.items():
        crow = run_cluster_pd2(cid, cinfo, pages, provider, rule_provider, guard, freeze)
        cluster_rows.append(crow)
    report = {'tool_version': TOOL_VERSION, 'freeze_sha256': sha256_bytes(args.freeze_path.read_bytes()),
              'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'model': args.model, 'clusters': cluster_rows,
              'budget': {'cap': guard.cap, 'freeze_cap': freeze['budget']['token_cap'],
                         'used': guard.used, 'calls': guard.calls, 'max_calls': guard.max_calls,
                         'skipped': guard.skipped},
              'note': 'P-G G3 real-page cluster-generalized repair + inline feedback; critic source_only v1.4.1; new stratum only; silver recall gate variants-only; natural pages no gold; G2 LSH hard-check FAIL disclosed; judge scores NOT rewards.'}
    write_json(args.output, report)
    statuses = {m['case_id']: m['status'] for c in cluster_rows for m in c['members']}
    print(json.dumps({'output': str(args.output), 'clusters': len(cluster_rows),
                      'statuses': statuses, 'tokens_used': guard.used, 'calls': guard.calls, 'cap': guard.cap}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
