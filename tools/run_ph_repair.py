# -*- coding: utf-8 -*-
"""P-H H1 guarded repair loop v1.1 (plan docs/P_H_PRE_PE_PLAN.md).

Derives the P-G G3 harness with TWO pre-registered gates (G3 honest-negative
driven; dev circularity disclosed, NOT an independent holdout):
  GATE-1 trigger: repair iff critic decision==fail OR any major/critical defect
    OR (silver expected exists AND baseline block_text_recall<1.0). Drift alone
    never triggers (kills redundant no_shared_rule repairs on good fallbacks).
  GATE-2 retention: when baseline decision!=fail, repaired must retain >=0.9 of
    baseline block texts (Counter recall) else repair is rejected, baseline kept,
    no rejudge call (over-exclusion protection).
Frozen helpers reused VERBATIM: reuse_pd2 / validate_feedback / Pd2Guard /
critic_feedback / run_agent / j141 (frozen modules zero rewrite; shas pinned).
Clusters from H2 ph.cluster.v1 (32x4 banding). Critic/rejudge v1.4.1 SOURCE_ONLY;
silver expected orchestrator-side only. Budget <=20 calls / 300k tokens.
Judge scores NOT training rewards. Refuses overwrite; --freeze requires quote.
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
from tools.run_pd2_generalize import reuse_pd2, Pd2Guard, _reuse_snapshot, MAX_REFS
from tools.run_pd_repair_loop import quality, validate_feedback
from tools.node5_loop import (critic_feedback, CriticGuidedProvider, audit_repair_prompt,
                              baseline_preview)
from src.webextractor.rule_agent import run_agent
from src.webextractor.rule_cache import ClusterRuleCache, apply_rule, fallback_extract
from collections import Counter

TOOL_VERSION = '1.1.0'
RETENTION_MIN = 0.9
PLAN_REL = 'docs/P_H_PRE_PE_PLAN.md'
CORPUS_REL = 'samples/pg_corpus.v1.json'
CLUSTER_REL = 'outputs/ph.cluster.v1.json'
FREEZE_REL = 'outputs/ph.repair.freeze.v1.json'
PARAMS = {'feature_mode': 'suffix-presence', 'drift_threshold': 0.7}
MODULE_PINS = {'judge_module_sha256': 'src/webextractor/rubrics_judge_v141.py',
               'v14_module_sha256': 'src/webextractor/rubrics_judge_v14.py',
               'rubrics_sha256': 'src/webextractor/rubrics_v2.py',
               'rule_agent_sha256': 'src/webextractor/rule_agent.py',
               'rule_cache_sha256': 'src/webextractor/rule_cache.py',
               'pd2_tool_sha256': 'tools/run_pd2_generalize.py',
               'pd_tool_sha256': 'tools/run_pd_repair_loop.py',
               'node5_tool_sha256': 'tools/node5_loop.py'}


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
        cid = 'ph-c%d' % ci
        clusters[cid] = {'rep': members[0], 'members': sorted(members), 'ref_ids': sorted(members)}
    return clusters


def make_freeze(approval_quote, cap=300000, corpus_rel=CORPUS_REL, cluster_rel=CLUSTER_REL):
    if not isinstance(approval_quote, str) or not approval_quote.strip():
        raise ValueError('--approval-quote must record the user approval text')
    pages, manifest = load_pg_pages(corpus_rel)
    clusters = load_clusters(cluster_rel)
    cases = [{'case_id': p['id'], 'html': p['html'], 'source_sha256': p['sha256'],
              'manual_group': p['manual_group'], 'source_kind': p['source_kind']}
             for p in manifest['pages']]
    return {'freeze_version': 'ph-repair-1',
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
            'trigger_rule': 'v1.1 GATE-1: repair iff decision==fail OR any major/critical defect OR (silver expected exists AND baseline block_text_recall<1.0); drift alone never triggers',
            'retention_gate': 'v1.1 GATE-2: when baseline decision!=fail, repaired must retain baseline block text (Counter recall >=0.9) else repair rejected and baseline kept (no rejudge call)',
            'classification': 'node5 frozen classify_pair (improved/regressed/no_effect/other_change; regressed priority)',
            'feedback_rule': 'improved AND rule unique+ok+nonempty on rep+every member AND recall not worse where silver expected exists; INLINE update on accept',
            'success_criteria': {'regression_rate_le': 0.10, 'retention_guard_violations_accepted_zero': True,
                                 'leakage_audit_all_passed': True, 'budget_respected': True,
                                 'verdict_labels': ['GUARDED_LOOP_SIGNAL', 'NO_GUARDED_LOOP_SIGNAL'],
                                 'note': 'H1 guarded loop v1.1; dev circularity disclosed (gates motivated by G3 regressions); improvement/trigger-reduction descriptive; NOT an independent holdout'},
            'budget': {'token_cap': cap, 'max_calls': 20, 'reserve_judge': 16000, 'reserve_rule': 8000},
            'seed': 20261119, 'B': 10000,
            'discipline': ['new stratum only; existing 13 snapshots clustering/reuse-only',
                           'G2 hard-check FAIL (LSH recall) disclosed; CL clusters valid (precision 1.0); no tuning',
                           'critic source_only; silver expected orchestrator-side only; never in prompts',
                           'repair <=1 intervention/member; no tuning; negative results honest',
                           'judge scores NOT training rewards', 'cluster purity != accuracy']}


def check_freeze(freeze, corpus_rel=CORPUS_REL, cluster_rel=CLUSTER_REL):
    problems = []
    if freeze.get('freeze_version') != 'ph-repair-1':
        problems.append('not a ph-repair-1 freeze')
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


def _text_retention(baseline, repaired):
    """GATE-2 metric: fraction of baseline block texts retained in repaired."""
    bt = [str(b.get('text', '')) for b in (baseline or {}).get('blocks', []) if b.get('text')]
    if not bt:
        return 1.0
    rt = Counter(str(b.get('text', '')) for b in (repaired or {}).get('blocks', []) if b.get('text'))
    return sum((Counter(bt) & rt).values()) / len(bt)


def run_member_ph(cluster_id, rep_id, member_id, ref_ids, pages, cache, provider, rule_provider, guard, freeze):
    p = freeze['protocol']
    page = pages[member_id]
    sb = page['source']
    expected = page['expected']
    row = {'cluster_id': cluster_id, 'case_id': member_id, 'rep_id': rep_id,
           'source_sha256': page['source_sha256'], 'repair': {'triggered': False}, 'calls': []}
    reuse = reuse_pd2(cache, cluster_id, member_id, sb, page['features'])
    row['reuse'] = {k: reuse[k] for k in ('reuse', 'fallback', 'drift', 'drift_reasons',
                                          'fingerprint_similarity', 'rule_status', 'final_status',
                                          'block_count', 'generalized_override')}
    baseline = reuse['extraction'] or {'title': '', 'blocks': []}
    row['baseline_candidate_sha256'] = sha256_json(baseline)
    row['baseline_quality'] = quality(baseline, expected)
    if not guard.allow('judge', member_id):
        row['status'] = 'skipped_budget'
        return row
    critic = j141.run_judge(sb, baseline, provider, gold=None,
                            max_source_chars=p['max_source_chars'], max_output_tokens=p['max_output_tokens'],
                            timeout_seconds=p['timeout_seconds'])
    guard.record(critic.get('usage'))
    guard.record_call()
    row['calls'].append({'kind': 'critic', 'usage': critic.get('usage'), 'status': critic.get('status')})
    row['critic'] = critic
    if critic.get('status') != 'accepted':
        row['status'] = 'critic_rejected'
        return row
    decision = critic['assessment']['decision']
    row['baseline_decision'] = decision
    fb = critic_feedback(critic)
    row['baseline_defect_count'] = len(fb['defects'])
    severe_defects = [d for d in fb['defects'] if d.get('severity') in ('major', 'critical')]
    bq = row.get('baseline_quality') or {}
    silver_low = expected is not None and bq.get('block_text_recall', 0) < 1.0
    if decision != 'fail' and not severe_defects and not silver_low:
        row['status'] = 'no_repair_needed'
        row['repair']['note'] = ('v1.1 GATE-1: acceptable baseline (decision=%s, severe_defects=0, silver_low=%s); drift=%s ignored'
                                 % (decision, silver_low, reuse['drift_reasons']))
        return row
    row['repair']['triggered'] = True
    row['repair']['trigger_reason'] = 'drift=%s;critic=%s;defects=%d' % (reuse['drift_reasons'], decision, len(fb['defects']))
    row['repair']['reference_ids'] = list(ref_ids)
    audit_log = []
    wrapped = CriticGuidedProvider(rule_provider, fb, baseline_preview(baseline), audit_log)
    if not guard.allow('rule', member_id):
        row['status'] = 'skipped_budget'
        return row
    references = [{'id': pid, 'source': pages[pid]['source'].decode('utf-8', errors='replace')}
                  for pid in ref_ids]
    trace = run_agent(references, wrapped,
                      max_attempts=p['rule_max_attempts'], execution_timeout=p['execution_timeout'],
                      total_timeout=p['total_timeout'], max_output_tokens=p['rule_max_output_tokens'],
                      evidence_chars=p['evidence_chars'])
    for att in trace.get('attempts', []):
        guard.record(att.get('usage'))
        guard.record_call()
        row['calls'].append({'kind': 'rule_generation', 'attempt': att.get('number'),
                             'usage': att.get('usage'), 'error': att.get('error')})
    row['repair']['trace'] = trace
    row['repair']['prompt_audit'] = [audit_repair_prompt(a['prompt'], critic) for a in audit_log]
    row['repair']['audit_log'] = audit_log
    if not trace.get('runtime_accepted') or not trace.get('selected_rule'):
        row['status'] = 'repair_failed'
        return row
    execution = next(e['execution'] for e in trace['attempts'][-1]['executions'] if e['id'] == member_id)
    result = execution.get('result') or {}
    repaired = {'title': result.get('title', ''), 'blocks': result.get('blocks') or []}
    row['repaired_candidate_sha256'] = sha256_json(repaired)
    row['repair']['selected_rule'] = trace['selected_rule']
    row['repaired_quality'] = quality(repaired, expected)
    if decision != 'fail':
        retention = _text_retention(baseline, repaired)
        row['repair']['retention_recall'] = retention
        if retention < RETENTION_MIN:
            row['status'] = 'repair_rejected_retention'
            row['repair']['guard'] = ('v1.1 GATE-2: baseline body retention %.3f < %.2f; baseline kept, no rejudge'
                                      % (retention, RETENTION_MIN))
            return row
    if not guard.allow('judge', member_id):
        row['status'] = 'skipped_budget'
        return row
    rejudge = j141.run_judge(sb, repaired, provider, gold=None,
                             max_source_chars=p['max_source_chars'], max_output_tokens=p['max_output_tokens'],
                             timeout_seconds=p['timeout_seconds'])
    guard.record(rejudge.get('usage'))
    guard.record_call()
    row['calls'].append({'kind': 'rejudge', 'usage': rejudge.get('usage'), 'status': rejudge.get('status')})
    row['rejudge'] = rejudge
    row['status'] = 'repaired' if rejudge.get('status') == 'accepted' else 'rejudge_rejected'
    return row


def run_cluster_ph(cluster_id, cinfo, pages, provider, rule_provider, guard, freeze):
    rep_id = cinfo['rep']
    member_ids = cinfo['members']
    ref_ids = cinfo.get('ref_ids') or sorted(set([rep_id] + member_ids))
    if len(ref_ids) > MAX_REFS:
        raise ValueError('cluster exceeds %d reference pages' % MAX_REFS)
    rep = pages[rep_id]
    cache = ClusterRuleCache(drift_threshold=freeze['params']['drift_threshold'])
    entry = cache.derive_and_cache(cluster_id, rep_id, rep['source'], rep['features'])
    layouts = sorted({pages[pid]['layout'] for pid in ref_ids})
    cluster_row = {'cluster_id': cluster_id, 'rep_id': rep_id, 'member_ids': member_ids,
                   'ref_ids': ref_ids, 'layouts': layouts, 'multi_layout': len(layouts) >= 2,
                   'shared_rule': entry['rule'], 'shared_rule_sha256': entry['rule_sha256'],
                   'members': [], 'feedback': {'attempted': False, 'accepted': False, 'events': []},
                   'member_rule_cache': {}}
    pre_recall = {}
    for pid in ref_ids:
        page = pages[pid]
        ap = apply_rule(page['source'], entry['rule']) if entry['rule'] else {'extraction': None}
        ex = ap.get('extraction') or fallback_extract(page['source'])['extraction']
        q = quality(ex, page['expected'])
        pre_recall[pid] = q['block_text_recall'] if q else None
    cluster_row['pre_recall'] = pre_recall
    cluster_row['v0_reuse'] = {pid: _reuse_snapshot(cache.reuse_member(cluster_id, pid, pages[pid]['source'], pages[pid]['features']), pages[pid]['expected'])
                               for pid in ref_ids}
    for mid in member_ids:
        mrow = run_member_ph(cluster_id, rep_id, mid, ref_ids, pages, cache, provider, rule_provider, guard, freeze)
        cluster_row['members'].append(mrow)
        rule = (mrow.get('repair') or {}).get('selected_rule')
        if mrow.get('status') == 'repaired' and rule:
            cluster_row['member_rule_cache'][mid] = rule
            bq = mrow.get('baseline_quality') or {}
            rq = mrow.get('repaired_quality') or {}
            improved_prog = rq.get('block_text_recall', 0) > bq.get('block_text_recall', 0)
            gen_ok, checks = validate_feedback(rule, rep_id, ref_ids, pages, pre_recall)
            ev = {'member_id': mid, 'rule': rule, 'programmatic_improved': improved_prog,
                  'generalizes': gen_ok, 'validation': checks, 'accepted': False}
            cluster_row['feedback']['attempted'] = True
            if improved_prog and gen_ok:
                cache.entries[cluster_id]['rule'] = rule
                cache.entries[cluster_id]['rule_sha256'] = sha256_json(rule)
                cache.entries[cluster_id]['generalized_validated'] = True
                ev['accepted'] = True
                ev['rereuse'] = {pid: _reuse_snapshot(reuse_pd2(cache, cluster_id, pid, pages[pid]['source'], pages[pid]['features']), pages[pid]['expected'])
                                 for pid in ref_ids}
                cluster_row['feedback']['accepted'] = True
                cluster_row['shared_rule'] = rule
                cluster_row['shared_rule_sha256'] = sha256_json(rule)
            else:
                ev['blocked_reason'] = 'not_improved' if not improved_prog else 'rule_does_not_generalize'
            cluster_row['feedback']['events'].append(ev)
    cluster_row['final_reuse'] = {pid: _reuse_snapshot(reuse_pd2(cache, cluster_id, pid, pages[pid]['source'], pages[pid]['features']), pages[pid]['expected'])
                                  for pid in ref_ids}
    recovery = [pid for pid in ref_ids
                if not cluster_row['v0_reuse'][pid]['reuse'] and cluster_row['final_reuse'][pid]['reuse']]
    cluster_row['reuse_recovery'] = recovery
    gen_calls = sum(1 for m in cluster_row['members'] for c in m['calls'] if c['kind'] == 'rule_generation')
    cluster_row['amortization'] = {'rule_generation_calls': gen_calls, 'recovered_members': len(recovery),
                                   'calls_per_recovered': round(gen_calls / len(recovery), 4) if recovery else None}
    return cluster_row


def main(argv=None):
    ap = argparse.ArgumentParser(description='P-H H1 guarded repair loop v1.1 (freeze required).')
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
        crow = run_cluster_ph(cid, cinfo, pages, provider, rule_provider, guard, freeze)
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
