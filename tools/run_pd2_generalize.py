# -*- coding: utf-8 -*-
"""P-D2 heterogeneous-cluster shared-rule generalization (plan docs/P_D2_GENERALIZATION_PLAN.md).

Upgrades P-D per-member repair to CLUSTER-GENERALIZED repair: the repairer sees
every cluster page source (<=8 references) and must produce ONE shared rule
(naturally a union XPath) that executes nonempty on every reference. Accepted
feedback updates the shared rule INLINE so later members reuse it (repair cost
amortized across the cluster). For feedback-validated generalized rules,
fingerprint_drift alone no longer invalidates reuse (layout heterogeneity is the
design goal); rule_failure still triggers drift+fallback. Critic/rejudge are
SOURCE_ONLY (gold=None); test/gold never reach the repairer; every repair prompt
is structurally leakage-audited; repair <=1 intervention per member. Feedback
validation uses dev expected on the orchestrator side only (never in prompts).
Judge scores are NOT training rewards. Refuses overwrite.
--freeze creates pd2.freeze.v1 (zero calls, requires --approval-quote); --run requires it.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.webextractor import rubrics_judge_v141 as j141
from src.webextractor.rule_cache import ClusterRuleCache, apply_rule, fallback_extract
from src.webextractor.rule_agent import run_agent
from src.webextractor.dom_similarity import structural_features
from tools.node5_loop import (critic_feedback, CriticGuidedProvider, audit_repair_prompt,
                              BudgetGuard, baseline_preview, sha256_bytes, sha256_json,
                              load_json, write_json)
from tools.run_rubrics_judge import _build_provider
from tools.run_pd_repair_loop import quality, validate_feedback, cluster_groups

TOOL_VERSION = '1.0.0'
FREEZE_REL = 'outputs/pd2.freeze.v1.json'
CORPUS_REL = 'samples/dom_similarity.controlled.v2.json'
PLAN_REL = 'docs/P_D2_GENERALIZATION_PLAN.md'
PARAMS = {'feature_mode': 'full-counts', 'drift_threshold': 0.7}
MAX_REFS = 8


def load_corpus():
    mp = ROOT / CORPUS_REL
    d = load_json(mp)
    pages = {}
    for p in d['pages']:
        sb = (mp.parent / p['html']).read_bytes()
        exp_path = mp.parent / 'drift_lab' / (p['id'] + '.expected.json')
        pages[p['id']] = {'id': p['id'], 'manual_group': p['manual_group'], 'layout': p['layout'],
                          'source': sb, 'source_sha256': sha256_bytes(sb), 'html': p['html'],
                          'expected': load_json(exp_path) if exp_path.exists() else None,
                          'features': structural_features(sb, PARAMS['feature_mode'])}
    return pages


def make_freeze(approval_quote, cap=200000):
    if not isinstance(approval_quote, str) or not approval_quote.strip():
        raise ValueError('--approval-quote must record the user approval text')
    pages = load_corpus()
    cases = []
    for pid, p in pages.items():
        row = {'case_id': pid, 'manual_group': p['manual_group'], 'layout': p['layout'],
               'html': p['html'], 'source_sha256': p['source_sha256']}
        if p['expected'] is not None:
            row['expected_sha256'] = sha256_bytes((ROOT / 'samples/drift_lab' / (pid + '.expected.json')).read_bytes())
        cases.append(row)
    return {
        'freeze_version': 'pd2-1',
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'approval': {'by': 'hqli631', 'quote': approval_quote},
        'preregistration': PLAN_REL,
        'plan_sha256': sha256_bytes((ROOT / PLAN_REL).read_bytes()),
        'corpus': CORPUS_REL, 'corpus_sha256': sha256_bytes((ROOT / CORPUS_REL).read_bytes()),
        'clusters': cluster_groups(pages), 'cases': cases, 'params': PARAMS,
        'protocol': {'model': 'qwen3.8-27b', 'judge_version': j141.JUDGE_VERSION,
                     'base_judge_version': '1.2.0', 'rubrics_version': '2.0.0',
                     'judge_module_sha256': sha256_bytes((ROOT / 'src/webextractor/rubrics_judge_v141.py').read_bytes()),
                     'v14_module_sha256': sha256_bytes((ROOT / 'src/webextractor/rubrics_judge_v14.py').read_bytes()),
                     'base_source_sha256': j141.BASE_SOURCE_SHA256,
                     'rubrics_sha256': sha256_bytes((ROOT / 'src/webextractor/rubrics_v2.py').read_bytes()),
                     'rule_agent_sha256': sha256_bytes((ROOT / 'src/webextractor/rule_agent.py').read_bytes()),
                     'rule_cache_sha256': sha256_bytes((ROOT / 'src/webextractor/rule_cache.py').read_bytes()),
                     'max_source_chars': 20000, 'max_output_tokens': 2200, 'timeout_seconds': 90,
                     'rule_max_attempts': 2, 'evidence_chars': 16000, 'rule_max_output_tokens': 1024,
                     'execution_timeout': 5.0, 'total_timeout': 120.0, 'critic_mode': 'source_only',
                     'generalized_repair': ('reference_pages = all cluster pages (<=8); one shared rule must '
                                            'execute nonempty on every reference (rule_agent runtime acceptance)'),
                     'generalized_reuse_semantics': ('for feedback-validated generalized rules, fingerprint_drift alone '
                                                     'does not invalidate; rule ok+nonempty -> reuse (generalized_override '
                                                     'recorded); rule_failure still triggers drift+fallback; v0 keeps P-C semantics')},
        'trigger_rule': ('repair iff drift_reasons non-empty OR critic decision==fail OR defects non-empty '
                         '(severity minor/major/critical or scored score<4); source_only never pass; '
                         'zero-defect uncertain without drift -> no_repair_needed'),
        'classification': 'reuses node5 frozen classify_pair (improved/regressed/no_effect/other_change; regressed priority; paired n = repaired with accepted rejudge)',
        'feedback_rule': ('feedback_accepted iff improved AND repaired rule apply_rule unique match + ok + block_count>0 '
                          'on rep AND every cluster page AND programmatic block_text_recall not worse than pre-repair; '
                          'INLINE: accepted feedback updates the shared rule immediately and later members reuse it; '
                          'else feedback_blocked with reason; per-page repaired rule retained in member cache'),
        'success_criteria': {'multi_layout_feedback_accepted_ge': 1, 'reuse_recovery_after_feedback_ge': 2,
                             'improvement_rate_ge': 1 / 3, 'regression_rate_le': 0.10,
                             'leakage_audit_all_passed': True, 'unnecessary_repair_zero': True,
                             'verdict_labels': ['GENERALIZATION_SIGNAL', 'NO_GENERALIZATION_SIGNAL'],
                             'note': 'descriptive signal, NOT a reward gate; small synthetic n, CI wide'},
        'budget': {'token_cap': cap, 'max_calls': 20, 'reserve_judge': 16000, 'reserve_rule': 8000},
        'seed': 20261119, 'B': 10000,
        'discipline': ['controlled synthetic drift_lab v2 only (7 pages); no real-site generalization claim',
                       'original five drift_lab fixtures byte-identical; P-D artifacts zero rewrite',
                       'protocol frozen during experiment; no tuning',
                       'test/gold never fed back; critic source_only; structural leakage audit',
                       'repair <=1 intervention per member (rule_agent max_attempts=2)',
                       'feedback validation uses dev expected orchestrator-side only, never in prompts',
                       'judge scores NOT training rewards', 'agreement != accuracy',
                       'negative results delivered honestly; no re-test chasing'],
    }


def check_freeze(freeze):
    problems = []
    if freeze.get('freeze_version') != 'pd2-1':
        problems.append('not a pd2-1 freeze')
    p = freeze.get('protocol') or {}
    pins = {'judge_module_sha256': 'src/webextractor/rubrics_judge_v141.py',
            'v14_module_sha256': 'src/webextractor/rubrics_judge_v14.py',
            'rubrics_sha256': 'src/webextractor/rubrics_v2.py',
            'rule_agent_sha256': 'src/webextractor/rule_agent.py',
            'rule_cache_sha256': 'src/webextractor/rule_cache.py'}
    for key, rel in pins.items():
        if p.get(key) != sha256_bytes((ROOT / rel).read_bytes()):
            problems.append('protocol sha drift: ' + rel)
    if p.get('base_source_sha256') != j141.BASE_SOURCE_SHA256:
        problems.append('v1.2 base sha drift')
    if p.get('judge_version') != j141.JUDGE_VERSION:
        problems.append('judge version drift')
    if freeze.get('corpus_sha256') != sha256_bytes((ROOT / CORPUS_REL).read_bytes()):
        problems.append('corpus drift')
    if freeze.get('plan_sha256') != sha256_bytes((ROOT / PLAN_REL).read_bytes()):
        problems.append('plan drift')
    for row in freeze.get('cases', []):
        sb = (ROOT / 'samples' / row['html']).read_bytes()
        if sha256_bytes(sb) != row['source_sha256']:
            problems.append('source drift ' + row['case_id'])
        if row.get('expected_sha256'):
            eb = (ROOT / 'samples/drift_lab' / (row['case_id'] + '.expected.json')).read_bytes()
            if sha256_bytes(eb) != row['expected_sha256']:
                problems.append('expected drift ' + row['case_id'])
    return problems


class Pd2Guard(BudgetGuard):
    """Token guard plus a hard model-call ceiling (freeze budget.max_calls)."""

    def __init__(self, cap, max_calls, reserve_judge=16000, reserve_rule=8000):
        super().__init__(cap, reserve_judge, reserve_rule)
        self.max_calls = max_calls
        self.calls = 0

    def allow(self, kind, case_id):
        if self.calls >= self.max_calls:
            self.skipped.append({'case_id': case_id, 'kind': kind, 'used': self.used, 'reason': 'max_calls'})
            return False
        return super().allow(kind, case_id)

    def record_call(self):
        self.calls += 1


def reuse_pd2(cache, cluster_id, member_id, source, features):
    """P-C reuse + frozen P-D2 generalized-rule override (plan section 5)."""
    entry = cache.entries[cluster_id]
    rr = cache.reuse_member(cluster_id, member_id, source, features)
    rr['generalized_override'] = False
    if (entry.get('generalized_validated') and rr['drift_reasons'] == ['fingerprint_drift']
            and rr['rule_status'] == 'ok'):
        ap = apply_rule(source, entry['rule'])
        if ap['status'] == 'ok' and ap['block_count'] > 0:
            rr.update(reuse=True, fallback=False, drift=False, drift_reasons=[],
                      extraction=ap['extraction'], final_status=ap['status'],
                      block_count=ap['block_count'], generalized_override=True)
    return rr


def _reuse_snapshot(rr, expected):
    return {'reuse': rr['reuse'], 'drift': rr['drift'], 'drift_reasons': rr['drift_reasons'],
            'rule_status': rr['rule_status'], 'final_status': rr['final_status'],
            'block_count': rr['block_count'], 'generalized_override': rr.get('generalized_override', False),
            'quality': quality(rr['extraction'], expected)}


def run_member_pd2(cluster_id, rep_id, member_id, ref_ids, pages, cache, provider, rule_provider, guard, freeze):
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
    drift = bool(reuse['drift_reasons'])
    if not drift and decision != 'fail' and not fb['defects']:
        row['status'] = 'no_repair_needed'
        row['repair']['note'] = 'no drift and zero defects -> no repair'
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


def run_cluster_pd2(cluster_id, cinfo, pages, provider, rule_provider, guard, freeze):
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
        mrow = run_member_pd2(cluster_id, rep_id, mid, ref_ids, pages, cache, provider, rule_provider, guard, freeze)
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
    ap = argparse.ArgumentParser(description='P-D2 heterogeneous-cluster generalized repair loop (freeze required).')
    ap.add_argument('--freeze', action='store_true', help='create pd2.freeze.v1 (zero calls)')
    ap.add_argument('--approval-quote', default=None, help='user approval text recorded in the freeze')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--freeze-path', type=Path, default=ROOT / FREEZE_REL)
    ap.add_argument('--output', type=Path, default=None)
    ap.add_argument('--max-cases', type=int, default=None)
    ap.add_argument('--only', default=None, help='evaluate only this member (smoke); repair refs still cover the full cluster')
    ap.add_argument('--model', default='qwen3.8-27b')
    ap.add_argument('--token-cap', type=int, default=None)
    args = ap.parse_args(argv)
    if args.freeze:
        if args.freeze_path.exists():
            print('Refusing to overwrite existing freeze.', file=sys.stderr)
            return 3
        try:
            fz = make_freeze(args.approval_quote)
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 1
        write_json(args.freeze_path, fz)
        print(json.dumps({'freeze': str(args.freeze_path), 'cases': len(fz['cases']),
                          'judge_version': fz['protocol']['judge_version'],
                          'token_cap': fz['budget']['token_cap'], 'max_calls': fz['budget']['max_calls']}, ensure_ascii=False))
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
    problems = check_freeze(freeze)
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
    pages = load_corpus()
    clusters = freeze['clusters']
    if args.only:
        target = None
        for cid, cinfo in clusters.items():
            if args.only in cinfo['members']:
                target = (cid, {'rep': cinfo['rep'], 'members': [args.only],
                                'ref_ids': sorted(set([cinfo['rep']] + cinfo['members']))})
                break
        if target is None:
            print('Unknown member: ' + args.only, file=sys.stderr)
            return 1
        clusters = {target[0]: target[1]}
    cluster_rows = []
    members_done = 0
    for cid, cinfo in clusters.items():
        if args.max_cases is not None and members_done >= args.max_cases:
            break
        cinfo2 = dict(cinfo)
        if args.max_cases is not None:
            cinfo2['members'] = cinfo['members'][:args.max_cases - members_done]
        crow = run_cluster_pd2(cid, cinfo2, pages, provider, rule_provider, guard, freeze)
        cluster_rows.append(crow)
        members_done += len(cinfo2['members'])
    report = {'tool_version': TOOL_VERSION, 'freeze_sha256': sha256_bytes(args.freeze_path.read_bytes()),
              'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'model': args.model, 'clusters': cluster_rows,
              'budget': {'cap': guard.cap, 'freeze_cap': freeze['budget']['token_cap'],
                         'used': guard.used, 'calls': guard.calls, 'max_calls': guard.max_calls,
                         'skipped': guard.skipped},
              'note': 'P-D2 cluster-generalized repair + inline feedback; critic source_only v1.4.1; repair<=1/member; leakage audited; judge scores NOT rewards; controlled synthetic corpus v2 (7 pages).'}
    write_json(args.output, report)
    statuses = {m['case_id']: m['status'] for c in cluster_rows for m in c['members']}
    print(json.dumps({'output': str(args.output), 'clusters': len(cluster_rows),
                      'statuses': statuses, 'tokens_used': guard.used, 'calls': guard.calls, 'cap': guard.cap}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
