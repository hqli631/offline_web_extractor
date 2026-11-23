# -*- coding: utf-8 -*-
"""P-D drift -> repair -> cluster-rule feedback closed loop (plan docs/P_D_REPAIR_LOOP_PLAN.md).

Upgrades P-C "drift -> fallback" to "drift -> v1.4.1 critic-guided rule repair ->
feedback validated repaired rule to the cluster cache -> reuse". Controlled
synthetic drift_lab corpus (mechanism-focused, NOT real-site generalization).
Critic/rejudge are SOURCE_ONLY (gold=None); test/gold never reach the repairer;
every repair prompt is structurally leakage-audited; repair <=1 intervention
(rule_agent max_attempts=2). Repaired rule is fed back as the cluster shared rule
ONLY if it improves quality AND validates (unique match + ok + nonempty + recall
not worse) on the representative and every member; otherwise it is retained as a
per-page repair with a disclosed feedback_blocked reason. Programmatic side-check
is post-hoc report-only. Judge scores are NOT training rewards. Refuses overwrite.
--freeze creates pd.freeze.v1 (zero calls); --run requires it.
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
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

TOOL_VERSION = '1.0.0'
FREEZE_REL = 'outputs/pd.freeze.v1.json'
CORPUS_REL = 'samples/dom_similarity.controlled.json'
PARAMS = {'feature_mode': 'full-counts', 'drift_threshold': 0.7}
SEVERE = ('major', 'critical')


def quality(extraction, expected):
    if extraction is None or expected is None:
        return None
    pt = Counter(b['text'] for b in extraction['blocks'])
    et = Counter(b['text'] for b in expected['blocks'])
    matched = sum((pt & et).values())
    np_, ne = sum(pt.values()), sum(et.values())
    return {'title_exact': extraction['title'] == expected['title'],
            'blocks_exact': extraction['blocks'] == expected['blocks'],
            'block_text_precision': round(matched / np_, 6) if np_ else 0.0,
            'block_text_recall': round(matched / ne, 6) if ne else 0.0}


def load_corpus():
    mp = ROOT / CORPUS_REL
    d = load_json(mp)
    pages = {}
    for p in d['pages']:
        sb = (mp.parent / p['html']).read_bytes()
        exp_path = mp.parent / 'drift_lab' / (p['id'] + '.expected.json')
        pages[p['id']] = {'id': p['id'], 'manual_group': p['manual_group'],
                          'source': sb, 'source_sha256': sha256_bytes(sb), 'html': p['html'],
                          'expected': load_json(exp_path) if exp_path.exists() else None,
                          'features': structural_features(sb, PARAMS['feature_mode'])}
    return pages


def cluster_groups(pages):
    groups = {}
    for pid, p in pages.items():
        groups.setdefault(p['manual_group'], []).append(pid)
    clusters = {}
    for g, members in groups.items():
        members = sorted(members)
        rep = 'reference' if 'reference' in members else members[0]
        # rep is the rule source AND is itself evaluated as a member (reuse its own
        # rule), so single-page families (content-moved, duplicate-main) are exercised.
        clusters[g] = {'rep': rep, 'members': members}
    return clusters


def make_freeze(cap=300000):
    pages = load_corpus()
    cases = []
    for pid, p in pages.items():
        row = {'case_id': pid, 'manual_group': p['manual_group'], 'html': p['html'],
               'source_sha256': p['source_sha256']}
        if p['expected'] is not None:
            row['expected_sha256'] = sha256_bytes((ROOT / 'samples/drift_lab' / (pid + '.expected.json')).read_bytes())
        cases.append(row)
    return {
        'freeze_version': 'pd-1',
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'approval': {'by': 'hqli631', 'at': '2026-11-23',
                     'quote': '开始P-D：漂移→修复→回灌簇规则闭环，批准合理的计划+预算，直至P-D基本完成'},
        'preregistration': 'docs/P_D_REPAIR_LOOP_PLAN.md',
        'plan_sha256': sha256_bytes((ROOT / 'docs/P_D_REPAIR_LOOP_PLAN.md').read_bytes()),
        'corpus': CORPUS_REL, 'corpus_sha256': sha256_bytes((ROOT / CORPUS_REL).read_bytes()),
        'clusters': cluster_groups(pages), 'cases': cases, 'params': PARAMS,
        'protocol': {'model': 'qwen3.8-27b', 'judge_version': j141.JUDGE_VERSION,
                     'base_judge_version': j141.BASE_JUDGE_VERSION, 'rubrics_version': j141.VERSION,
                     'judge_module_sha256': sha256_bytes((ROOT / 'src/webextractor/rubrics_judge_v141.py').read_bytes()),
                     'v14_module_sha256': sha256_bytes((ROOT / 'src/webextractor/rubrics_judge_v14.py').read_bytes()),
                     'base_source_sha256': j141.BASE_SOURCE_SHA256,
                     'rubrics_sha256': sha256_bytes((ROOT / 'src/webextractor/rubrics_v2.py').read_bytes()),
                     'rule_agent_sha256': sha256_bytes((ROOT / 'src/webextractor/rule_agent.py').read_bytes()),
                     'rule_cache_sha256': sha256_bytes((ROOT / 'src/webextractor/rule_cache.py').read_bytes()),
                     'max_source_chars': 20000, 'max_output_tokens': 2200, 'timeout_seconds': 90,
                     'rule_max_attempts': 2, 'evidence_chars': 16000, 'rule_max_output_tokens': 1024,
                     'execution_timeout': 5.0, 'total_timeout': 120.0, 'critic_mode': 'source_only'},
        'trigger_rule': ('repair iff drift_reasons non-empty OR critic decision==fail OR defects non-empty '
                         '(severity minor/major/critical or scored score<4); source_only never pass; '
                         'zero-defect uncertain without drift -> no_repair_needed'),
        'classification': 'reuses node5 frozen classify_pair (improved/regressed/no_effect/other_change; regressed priority; paired n = repaired with accepted rejudge)',
        'feedback_rule': ('feedback_accepted iff improved AND repaired rule apply_rule unique match + ok + block_count>0 '
                          'on rep AND every member AND programmatic block_text_recall not worse than member pre-repair; '
                          'else feedback_blocked with reason; per-page repaired rule retained in member cache'),
        'success_criteria': {'improvement_rate_ge': 1 / 3, 'regression_rate_le': 0.10,
                             'leakage_audit_all_passed': True, 'unnecessary_repair_zero': True,
                             'drift_recovery_case': 'role-drift',
                             'verdict_labels': ['REPAIR_BENEFIT_SIGNAL', 'NO_BENEFIT_SIGNAL'],
                             'note': 'descriptive signal, NOT a reward gate; small synthetic n, CI wide'},
        'budget': {'token_cap': cap, 'max_calls': 25, 'reserve_judge': 16000, 'reserve_rule': 8000},
        'seed': 20261119, 'B': 10000,
        'discipline': ['controlled synthetic drift_lab only; no real-site generalization claim',
                       'protocol frozen during experiment; no tuning',
                       'test/gold never fed back; critic source_only; structural leakage audit',
                       'repair <=1 intervention (rule_agent max_attempts=2)',
                       'judge scores NOT training rewards', 'agreement != accuracy',
                       'negative results delivered honestly; no re-test chasing'],
    }


def check_freeze(freeze):
    problems = []
    if freeze.get('freeze_version') != 'pd-1':
        problems.append('not a pd-1 freeze')
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
    if freeze.get('plan_sha256') != sha256_bytes((ROOT / 'docs/P_D_REPAIR_LOOP_PLAN.md').read_bytes()):
        problems.append('plan drift')
    for row in freeze.get('cases', []):
        sb = (ROOT / 'samples' / row['html']).read_bytes()
        if sha256_bytes(sb) != row['source_sha256']:
            problems.append('source drift ' + row['case_id'])
    return problems


def run_member(cluster_id, rep_id, member_id, pages, cache, provider, rule_provider, guard, freeze):
    p = freeze['protocol']
    page = pages[member_id]
    sb = page['source']
    text = sb.decode('utf-8', errors='replace')
    expected = page['expected']
    row = {'cluster_id': cluster_id, 'case_id': member_id, 'rep_id': rep_id,
           'source_sha256': page['source_sha256'], 'repair': {'triggered': False}, 'calls': []}
    reuse = cache.reuse_member(cluster_id, member_id, sb, page['features'])
    row['reuse'] = {k: reuse[k] for k in ('reuse', 'fallback', 'drift', 'drift_reasons',
                                          'fingerprint_similarity', 'rule_status', 'final_status', 'block_count')}
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
    audit_log = []
    wrapped = CriticGuidedProvider(rule_provider, fb, baseline_preview(baseline), audit_log)
    if not guard.allow('rule', member_id):
        row['status'] = 'skipped_budget'
        return row
    trace = run_agent([{'id': member_id, 'source': text}], wrapped,
                      max_attempts=p['rule_max_attempts'], execution_timeout=p['execution_timeout'],
                      total_timeout=p['total_timeout'], max_output_tokens=p['rule_max_output_tokens'],
                      evidence_chars=p['evidence_chars'])
    for att in trace.get('attempts', []):
        guard.record(att.get('usage'))
        row['calls'].append({'kind': 'rule_generation', 'attempt': att.get('number'),
                             'usage': att.get('usage'), 'error': att.get('error')})
    row['repair']['trace'] = trace
    row['repair']['prompt_audit'] = [audit_repair_prompt(a['prompt'], critic) for a in audit_log]
    row['repair']['audit_log'] = audit_log
    if not trace.get('runtime_accepted') or not trace.get('selected_rule'):
        row['status'] = 'repair_failed'
        return row
    execution = trace['attempts'][-1]['executions'][0]['execution']
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
    row['calls'].append({'kind': 'rejudge', 'usage': rejudge.get('usage'), 'status': rejudge.get('status')})
    row['rejudge'] = rejudge
    row['status'] = 'repaired' if rejudge.get('status') == 'accepted' else 'rejudge_rejected'
    return row


def validate_feedback(rule, rep_id, member_ids, pages, pre_recall):
    """Repaired rule generalizes iff unique match + ok + nonempty + recall not worse on rep + every member."""
    checks = []
    ok = True
    for pid in sorted(set([rep_id] + member_ids)):
        page = pages[pid]
        ap = apply_rule(page['source'], rule)
        q = quality(ap['extraction'], page['expected'])
        recall = q['block_text_recall'] if q else None
        pre = pre_recall.get(pid)
        recall_ok = (pre is None) or (recall is not None and recall >= pre)
        good = ap['status'] == 'ok' and ap['match_count'] == 1 and ap['block_count'] > 0 and recall_ok
        checks.append({'case_id': pid, 'rule_status': ap['status'], 'match_count': ap['match_count'],
                       'block_count': ap['block_count'], 'recall': recall, 'pre_recall': pre, 'pass': good})
        if not good:
            ok = False
    return ok, checks


def run_cluster(cluster_id, cinfo, pages, provider, rule_provider, guard, freeze):
    rep_id = cinfo['rep']
    member_ids = cinfo['members']
    rep = pages[rep_id]
    cache = ClusterRuleCache(drift_threshold=freeze['params']['drift_threshold'])
    entry = cache.derive_and_cache(cluster_id, rep_id, rep['source'], rep['features'])
    cluster_row = {'cluster_id': cluster_id, 'rep_id': rep_id, 'member_ids': member_ids,
                   'shared_rule': entry['rule'], 'shared_rule_sha256': entry['rule_sha256'],
                   'members': [], 'feedback': {'attempted': False}, 'member_rule_cache': {}}
    pre_recall = {}
    for pid in sorted(set([rep_id] + member_ids)):
        page = pages[pid]
        ap = apply_rule(page['source'], entry['rule']) if entry['rule'] else {'extraction': None}
        ex = ap.get('extraction') or fallback_extract(page['source'])['extraction']
        q = quality(ex, page['expected'])
        pre_recall[pid] = q['block_text_recall'] if q else None
    cluster_row['pre_recall'] = pre_recall
    repaired_rules = {}
    for mid in member_ids:
        mrow = run_member(cluster_id, rep_id, mid, pages, cache, provider, rule_provider, guard, freeze)
        cluster_row['members'].append(mrow)
        if mrow.get('status') == 'repaired' and (mrow.get('repair') or {}).get('selected_rule'):
            repaired_rules[mid] = mrow['repair']['selected_rule']
    for mid, rule in repaired_rules.items():
        mrow = next(m for m in cluster_row['members'] if m['case_id'] == mid)
        bq = mrow.get('baseline_quality') or {}
        rq = mrow.get('repaired_quality') or {}
        improved_prog = rq.get('block_text_recall', 0) > bq.get('block_text_recall', 0)
        gen_ok, checks = validate_feedback(rule, rep_id, member_ids, pages, pre_recall)
        fb = {'member_id': mid, 'rule': rule, 'programmatic_improved': improved_prog,
              'generalizes': gen_ok, 'validation': checks}
        cluster_row['member_rule_cache'][mid] = rule
        if improved_prog and gen_ok:
            cache.entries[cluster_id]['rule'] = rule
            cache.entries[cluster_id]['rule_sha256'] = sha256_json(rule)
            fb['accepted'] = True
            rereuse = []
            for mid2 in member_ids:
                rr = cache.reuse_member(cluster_id, mid2, pages[mid2]['source'], pages[mid2]['features'])
                rereuse.append({'case_id': mid2, 'reuse': rr['reuse'], 'drift': rr['drift'],
                                'final_status': rr['final_status'], 'block_count': rr['block_count'],
                                'quality': quality(rr['extraction'], pages[mid2]['expected'])})
            fb['rereuse'] = rereuse
            cluster_row['feedback'] = {'attempted': True, 'accepted': True, 'detail': fb}
        else:
            fb['accepted'] = False
            fb['blocked_reason'] = 'not_improved' if not improved_prog else 'rule_does_not_generalize'
            cluster_row['feedback'] = {'attempted': True, 'accepted': False, 'detail': fb}
        break
    return cluster_row


def main(argv=None):
    ap = argparse.ArgumentParser(description='P-D drift->repair->cluster-rule feedback closed loop (freeze required).')
    ap.add_argument('--freeze', action='store_true', help='create pd.freeze.v1 (zero calls)')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--freeze-path', type=Path, default=ROOT / FREEZE_REL)
    ap.add_argument('--output', type=Path, default=None)
    ap.add_argument('--max-cases', type=int, default=None)
    ap.add_argument('--only', default=None, help='run only this member id (smoke)')
    ap.add_argument('--model', default='qwen3.8-27b')
    ap.add_argument('--token-cap', type=int, default=None)
    args = ap.parse_args(argv)
    if args.freeze:
        if args.freeze_path.exists():
            print('Refusing to overwrite existing freeze.', file=sys.stderr)
            return 3
        fz = make_freeze()
        write_json(args.freeze_path, fz)
        print(json.dumps({'freeze': str(args.freeze_path), 'cases': len(fz['cases']),
                          'judge_version': fz['protocol']['judge_version'],
                          'token_cap': fz['budget']['token_cap']}, ensure_ascii=False))
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
    guard = BudgetGuard(cap, freeze['budget']['reserve_judge'], freeze['budget']['reserve_rule'])
    pages = load_corpus()
    clusters = freeze['clusters']
    if args.only:
        target = None
        for cid, cinfo in clusters.items():
            if args.only in cinfo['members']:
                target = (cid, {'rep': cinfo['rep'], 'members': [args.only]})
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
        crow = run_cluster(cid, cinfo2, pages, provider, rule_provider, guard, freeze)
        cluster_rows.append(crow)
        members_done += len(cinfo2['members'])
    report = {'tool_version': TOOL_VERSION, 'freeze_sha256': sha256_bytes(args.freeze_path.read_bytes()),
              'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'model': args.model, 'clusters': cluster_rows,
              'budget': {'cap': guard.cap, 'freeze_cap': freeze['budget']['token_cap'],
                         'used': guard.used, 'skipped': guard.skipped},
              'note': 'P-D drift->repair->cluster-rule feedback; critic source_only v1.4.1; repair<=1; leakage audited; judge scores NOT rewards; controlled synthetic corpus.'}
    write_json(args.output, report)
    statuses = {m['case_id']: m['status'] for c in cluster_rows for m in c['members']}
    print(json.dumps({'output': str(args.output), 'clusters': len(cluster_rows),
                      'statuses': statuses, 'tokens_used': guard.used, 'cap': guard.cap}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
