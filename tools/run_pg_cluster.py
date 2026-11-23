# -*- coding: utf-8 -*-
"""P-G G2 clustering harness: suffix-presence protocol adoption validation.

Pre-registered params (plan docs/P_G_REAL_TEMPLATE_PLAN.md): feature_mode=
suffix-presence (adoption motivated by P-C post-hoc ablation; validated here on
NEW independently collected families, not tuned), threshold=0.7, complete-linkage,
MinHash num_perm=128/seed=20261123, LSH bands=16xrows=8, drift_threshold=0.7.
Stratified metrics: all (mixed 28) / new (collected + variants) / existing (13
snapshots, comparable to P-C full-counts baseline 0.077/0.122 and suffix ablation
0.538/0.660 on the SAME pages - disclosed adoption check). Hard checks: CL
anti-chaining violations = 0 and LSH positive recall >= 0.9 per stratum.
Descriptive expectation (NOT a gate): new-stratum pair recall >= 0.5.
Zero model calls, zero network. Refuses overwrite. --freeze requires approval quote.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.run_pc_cluster_loop import load_pages, run_corpus
from tools.node5_loop import sha256_bytes, load_json, write_json

TOOL_VERSION = '1.0.0'
PLAN_REL = 'docs/P_G_REAL_TEMPLATE_PLAN.md'
CORPUS_REL = 'samples/pg_corpus.v1.json'
FREEZE_REL = 'outputs/pg.cluster.freeze.v1.json'
PARAMS = {'feature_mode': 'suffix-presence', 'threshold': 0.7, 'num_perm': 128,
          'seed': 20261123, 'bands': 16, 'rows': 8, 'drift_threshold': 0.7}
MODULE_PINS = {'dom_similarity_sha256': 'src/webextractor/dom_similarity.py',
               'dom_lsh_sha256': 'src/webextractor/dom_lsh.py',
               'dom_cluster_sha256': 'src/webextractor/dom_cluster.py',
               'rule_cache_sha256': 'src/webextractor/rule_cache.py'}


def make_freeze(approval_quote, corpus_rel=CORPUS_REL):
    if not isinstance(approval_quote, str) or not approval_quote.strip():
        raise ValueError('--approval-quote must record the user approval text')
    mp = ROOT / corpus_rel
    manifest = load_json(mp)
    cases = [{'case_id': p['id'], 'html': p['html'], 'source_sha256': p['sha256'],
              'manual_group': p['manual_group'], 'source_kind': p['source_kind']}
             for p in manifest['pages']]
    return {'freeze_version': 'pg-cluster-1',
            'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'approval': {'by': 'hqli631', 'quote': approval_quote},
            'preregistration': PLAN_REL, 'plan_sha256': sha256_bytes((ROOT / PLAN_REL).read_bytes()),
            'corpus': corpus_rel, 'corpus_sha256': sha256_bytes(mp.read_bytes()),
            'strata': manifest['strata'], 'cases': cases, 'params': PARAMS,
            'protocol': {k: sha256_bytes((ROOT / rel).read_bytes()) for k, rel in MODULE_PINS.items()},
            'hard_checks': {'cl_anti_chaining_violations_zero': True, 'lsh_positive_recall_ge': 0.9},
            'descriptive_expectations': {'new_stratum_pair_recall_ge': 0.5,
                                         'note': 'expectation motivated by P-C ablation; reported, NOT a gate'},
            'budget': {'g1_fetch_cap': 20, 'g2_model_calls': 0, 'g2_network': 0},
            'discipline': ['suffix-presence adoption validated on new corpus; no tuning',
                           'existing 13 snapshots byte-identical; clustering/reuse only',
                           'silver expected (variants) orchestrator-side only; never in prompts',
                           'cluster purity != extraction accuracy', 'judge scores NOT training rewards',
                           'negative results delivered honestly']}


def check_freeze(freeze, corpus_rel=CORPUS_REL):
    problems = []
    if freeze.get('freeze_version') != 'pg-cluster-1':
        problems.append('not a pg-cluster-1 freeze')
    for key, rel in MODULE_PINS.items():
        if (freeze.get('protocol') or {}).get(key) != sha256_bytes((ROOT / rel).read_bytes()):
            problems.append('protocol sha drift: ' + rel)
    if freeze.get('plan_sha256') != sha256_bytes((ROOT / PLAN_REL).read_bytes()):
        problems.append('plan drift')
    mp = ROOT / corpus_rel
    if freeze.get('corpus_sha256') != sha256_bytes(mp.read_bytes()):
        problems.append('corpus drift')
    manifest = load_json(mp)
    by_id = {p['id']: p for p in manifest['pages']}
    for row in freeze.get('cases', []):
        p = by_id.get(row['case_id'])
        if p is None or p['sha256'] != row['source_sha256']:
            problems.append('source drift ' + row['case_id'])
    return problems


def run_strata(manifest_path, freeze):
    manifest_path = Path(manifest_path)
    pages_all = load_pages(manifest_path, PARAMS['feature_mode'])
    by_id = {p['id']: p for p in pages_all}
    expected_dir = ROOT / 'samples' / 'pg_v1'
    strata = {}
    for name, ids in freeze['strata'].items():
        subset = [by_id[i] for i in sorted(ids) if i in by_id]
        res = run_corpus(subset, manifest_path, expected_dir, PARAMS)
        res['stratum_ids'] = sorted(ids)
        strata[name] = res
    hard = {}
    for name, res in strata.items():
        violations = len(res['complete_linkage']['anti_chaining_violations'])
        recall = res['lsh']['candidate_recall_of_exact_positives']
        hard[name] = {'cl_anti_chaining_violations': violations,
                      'cl_violations_zero': violations == 0,
                      'lsh_positive_recall': recall,
                      'lsh_recall_ge_0_9': recall >= freeze['hard_checks']['lsh_positive_recall_ge']}
    hard_pass = all(h['cl_violations_zero'] and h['lsh_recall_ge_0_9'] for h in hard.values())
    new_recall = strata['new']['cluster_purity']['pair_recall'] if 'new' in strata else None
    expectations = {'new_stratum_pair_recall': new_recall,
                    'new_stratum_pair_recall_ge_0_5': (new_recall is not None and new_recall >= 0.5),
                    'note': 'descriptive expectation, NOT a gate'}
    return {'tool_version': TOOL_VERSION, 'freeze_sha256': freeze.get('_freeze_sha256'),
            'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'params': PARAMS, 'strata': strata, 'hard_checks': hard,
            'descriptive_expectations': expectations,
            'verdict': 'G2_HARD_CHECKS_PASS' if hard_pass else 'G2_HARD_CHECKS_FAIL',
            'note': ('P-G G2 suffix-presence adoption validation; stratified all/new/existing; '
                     'existing stratum comparable to P-C full-counts baseline and suffix ablation (same pages); '
                     'cluster purity != accuracy; silver expected variants orchestrator-side only; '
                     '28 pages not production scale; LSH scale benefit descriptive; judge scores NOT rewards.')}


def main(argv=None):
    ap = argparse.ArgumentParser(description='P-G G2 clustering harness (zero calls/network).')
    ap.add_argument('--freeze', action='store_true')
    ap.add_argument('--approval-quote', default=None)
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--freeze-path', type=Path, default=ROOT / FREEZE_REL)
    ap.add_argument('--corpus', type=Path, default=ROOT / CORPUS_REL)
    ap.add_argument('--output', type=Path, default=None)
    args = ap.parse_args(argv)
    if args.freeze:
        if args.freeze_path.exists():
            print('Refusing to overwrite existing freeze.', file=sys.stderr)
            return 3
        try:
            fz = make_freeze(args.approval_quote, str(args.corpus.relative_to(ROOT)) if args.corpus.is_absolute() else str(args.corpus))
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 1
        write_json(args.freeze_path, fz)
        print(json.dumps({'freeze': str(args.freeze_path), 'cases': len(fz['cases']),
                          'feature_mode': fz['params']['feature_mode']}, ensure_ascii=False))
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
    corpus_rel = str(args.corpus.relative_to(ROOT)) if args.corpus.is_absolute() else str(args.corpus)
    problems = check_freeze(freeze, corpus_rel)
    if problems:
        for pr in problems:
            print('FREEZE: ' + pr, file=sys.stderr)
        return 1
    freeze['_freeze_sha256'] = sha256_bytes(args.freeze_path.read_bytes())
    result = run_strata(args.corpus, freeze)
    write_json(args.output, result)
    summary = {s: {'pages': r['n_pages'], 'clusters': len(r['complete_linkage']['clusters']),
                   'pair_precision': r['cluster_purity']['pair_precision'],
                   'pair_recall': r['cluster_purity']['pair_recall'],
                   'ari': r['cluster_purity']['ari'],
                   'lsh_recall': r['lsh']['candidate_recall_of_exact_positives'],
                   'reuse_rate': r['rule_reuse']['reuse_rate'],
                   'savings_proxy': r['rule_reuse']['derivation_savings_proxy']}
               for s, r in result['strata'].items()}
    print(json.dumps({'output': str(args.output), 'verdict': result['verdict'],
                      'strata': summary, 'hard_checks': result['hard_checks'],
                      'expectations': result['descriptive_expectations']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
