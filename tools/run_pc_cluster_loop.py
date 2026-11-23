"""P-C closed-loop harness: fingerprint -> LSH -> complete-linkage -> shared-rule
cache -> execute/validate/fallback/drift -> metrics. Zero model calls, zero network.

Definitive clustering uses exact pairwise Jaccard (small corpus); MinHash-LSH is
validated as a recall-oriented candidate filter (the cost-amortization mechanism
for massive pages). Real and synthetic corpora are reported separately. Cluster
purity is not extraction accuracy; unique rule match is not content completeness.
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.webextractor.dom_similarity import structural_features, FEATURE_MODES
from src.webextractor.dom_lsh import minhash_signature, lsh_candidate_pairs
from src.webextractor.dom_cluster import complete_linkage, pairwise_similarity
from src.webextractor.rule_cache import ClusterRuleCache

TOOL_VERSION = '1.1.0'
PARAMS = {'threshold': 0.7, 'feature_mode': 'full-counts', 'num_perm': 128,
          'seed': 20261123, 'bands': 16, 'rows': 8, 'drift_threshold': 0.7}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load_pages(manifest_path, feature_mode=None):
    manifest_path = Path(manifest_path)
    d = json.loads(manifest_path.read_text(encoding='utf-8'))
    pages = []
    for p in d['pages']:
        source = (manifest_path.parent / p['html']).read_bytes()
        pages.append({'id': p['id'], 'manual_group': p['manual_group'],
                      'source_kind': p['source_kind'], 'source': source,
                      'html': p['html'],
                      'features': structural_features(source, feature_mode or PARAMS['feature_mode'])})
    return pages


def connected_components_cc(ids, sim, threshold):
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for (a, b), s in sim.items():
        if s >= threshold:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
    comps = {}
    for i in ids:
        comps.setdefault(find(i), []).append(i)
    components = [sorted(v) for v in comps.values()]
    chaining = []
    for c in components:
        for a, b in combinations(c, 2):
            s = sim[(a, b) if a < b else (b, a)]
            if s < threshold:
                chaining.append({'component': c, 'below_threshold_pair': [a, b],
                                 'similarity': round(s, 6)})
                break
    return components, chaining


def _comb2(n):
    return n * (n - 1) // 2


def adjusted_rand_index(clusters, groups):
    ids = sorted(groups)
    cl = {i: ci for ci, c in enumerate(clusters) for i in c}
    gnames = sorted(set(groups.values()))
    gl = {i: gi for gi, g in enumerate(gnames) for i in ids if groups[i] == g}
    cont = Counter((cl[i], gl[i]) for i in ids)
    sum_nij = sum(_comb2(n) for n in cont.values())
    a = Counter(cl[i] for i in ids)
    b = Counter(gl[i] for i in ids)
    sum_a = sum(_comb2(n) for n in a.values())
    sum_b = sum(_comb2(n) for n in b.values())
    total = _comb2(len(ids))
    if total == 0:
        return 1.0
    expected = sum_a * sum_b / total
    max_index = (sum_a + sum_b) / 2
    denom = max_index - expected
    return (sum_nij - expected) / denom if denom else 1.0


def pair_metrics(clusters, groups):
    ids = sorted(groups)
    true_same = {(a, b) for a, b in combinations(ids, 2) if groups[a] == groups[b]}
    pred_same = set()
    for c in clusters:
        for a, b in combinations(sorted(c), 2):
            pred_same.add((a, b))
    tp = len(pred_same & true_same)
    precision = tp / len(pred_same) if pred_same else 1.0
    recall = tp / len(true_same) if true_same else 1.0
    return {'pair_precision': round(precision, 6), 'pair_recall': round(recall, 6),
            'true_same_pairs': len(true_same), 'pred_same_pairs': len(pred_same),
            'tp': tp, 'ari': round(adjusted_rand_index(clusters, groups), 6)}


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


def run_corpus(pages, manifest_path, expected_dir=None, params=None):
    params = params or PARAMS
    thr = params['threshold']
    fby = {p['id']: p['features'] for p in pages}
    groups = {p['id']: p['manual_group'] for p in pages}
    sim = pairwise_similarity(fby)
    sigs = {p['id']: minhash_signature(p['features'], params['num_perm'], params['seed'])
            for p in pages}
    lsh = lsh_candidate_pairs(sigs, params['bands'], params['rows'])
    exact_pos = {pair for pair, s in sim.items() if s >= thr}
    lsh_recall = len(lsh & exact_pos) / len(exact_pos) if exact_pos else 1.0
    cl = complete_linkage(fby, thr, sim=sim)
    cc, chaining = connected_components_cc(sorted(fby), sim, thr)
    purity = pair_metrics(cl['clusters'], groups)
    cache = ClusterRuleCache(params['drift_threshold'])
    by_id = {p['id']: p for p in pages}
    members = []
    rule_derivations = 0
    for ci, cluster in enumerate(cl['clusters']):
        cid = 'c%d' % ci
        rep = cluster[0]
        entry = cache.derive_and_cache(cid, rep, by_id[rep]['source'], fby[rep])
        if entry['rule'] is not None:
            rule_derivations += 1
        for mid in cluster:
            out = cache.reuse_member(cid, mid, by_id[mid]['source'], fby[mid])
            expected = None
            if expected_dir is not None:
                ep = Path(expected_dir) / (mid + '.expected.json')
                if ep.exists():
                    expected = json.loads(ep.read_text(encoding='utf-8'))
            out['is_representative'] = mid == rep
            out['manual_group'] = groups[mid]
            out['cluster'] = cid
            out['quality'] = quality(out['extraction'], expected)
            members.append(out)
    eligible = [m for m in members if not m['is_representative']
                and len(cl['clusters'][int(m['cluster'][1:])]) > 1]
    reuse_success = sum(m['reuse'] for m in eligible)
    fallback_count = sum(m['fallback'] for m in members)
    drift_count = sum(m['drift'] for m in members)
    n = len(pages)
    family = {}
    for g in sorted(set(groups.values())):
        gids = sorted(i for i in groups if groups[i] == g)
        landed = sorted({m['cluster'] for m in members if m['manual_group'] == g})
        family[g] = {'members': gids, 'clusters': landed, 'size': len(gids)}
    return {
        'n_pages': n, 'params': params,
        'manifest_sha256': sha(Path(manifest_path).read_bytes()),
        'lsh': {'candidate_pairs': len(lsh), 'full_pairs': len(sim),
                'exact_positive_pairs': len(exact_pos),
                'candidate_recall_of_exact_positives': round(lsh_recall, 6),
                'candidates': sorted([list(p) for p in lsh])},
        'complete_linkage': cl,
        'connected_components': {'components': cc, 'chaining_warnings': chaining,
                                 'n_components': len(cc), 'n_chaining': len(chaining)},
        'cluster_purity': purity,
        'rule_reuse': {'rule_derivations': rule_derivations, 'n_pages': n,
                       'derivation_savings_proxy': round(1 - rule_derivations / n, 6) if n else 0.0,
                       'eligible_transfer_members': len(eligible),
                       'reuse_success': reuse_success,
                       'reuse_rate': round(reuse_success / len(eligible), 6) if eligible else None,
                       'fallback_count': fallback_count,
                       'fallback_rate': round(fallback_count / n, 6) if n else 0.0,
                       'drift_count': drift_count},
        'family_summary': family,
        'members': members,
    }


def render_report(result):
    lines = ['# P-C 聚簇 + 同簇规则复用闭环报告', '',
             '冻结参数：`' + json.dumps(result['params'], ensure_ascii=False) + '`', '',
             '零模型调用、零网络。真实与合成分母分离；簇纯度≠提取准确率；唯一匹配≠正文完整。', '']
    for label in ('real', 'controlled'):
        c = result['corpora'][label]
        lines += ['## %s 语料（%d 页）' % (label, c['n_pages']), '',
                  '- complete-linkage 簇：`' + json.dumps(c['complete_linkage']['clusters'], ensure_ascii=False) + '`',
                  '- 抗链式违规：%d；连通分量：%d（链式警告 %d）' % (
                      len(c['complete_linkage']['anti_chaining_violations']),
                      c['connected_components']['n_components'], c['connected_components']['n_chaining']),
                  '- 簇纯度：精度 %.4f / 召回 %.4f / ARI %.4f' % (
                      c['cluster_purity']['pair_precision'], c['cluster_purity']['pair_recall'],
                      c['cluster_purity']['ari']),
                  '- LSH：候选 %d / 全对 %d；对精确≥0.7 正例召回 %.4f' % (
                      c['lsh']['candidate_pairs'], c['lsh']['full_pairs'],
                      c['lsh']['candidate_recall_of_exact_positives']),
                  '- 规则复用：派生 %d 次 / %d 页（节省代理 %.4f）；转移成员复用率 %s；回退 %d（%.4f）；漂移 %d' % (
                      c['rule_reuse']['rule_derivations'], c['rule_reuse']['n_pages'],
                      c['rule_reuse']['derivation_savings_proxy'],
                      str(c['rule_reuse']['reuse_rate']), c['rule_reuse']['fallback_count'],
                      c['rule_reuse']['fallback_rate'], c['rule_reuse']['drift_count']), '',
                  '| 成员 | 簇 | 代表 | 复用 | 回退 | 漂移 | 指纹相似 | 规则状态 | 原因 |',
                  '| --- | --- | --- | --- | --- | --- | ---: | --- | --- |']
        for m in c['members']:
            lines.append('| %s | %s | %s | %s | %s | %s | %.3f | %s | %s |' % (
                m['member_id'], m['cluster'], 'Y' if m['is_representative'] else '',
                m['reuse'], m['fallback'], m['drift'], m['fingerprint_similarity'],
                m['rule_status'], ','.join(m['drift_reasons'])))
        lines.append('')
    lines += ['## 局限', '',
              '- 小语料（real 13 + synthetic 5），非生产规模；"千亿级"仅业务语境。',
              '- iana-help 为跨站评估族（同属 development manifest），非严格独立采集 holdout；阈值 0.7 继承先前冻结消融。',
              '- 确定性规则派生器是结构化启发式（非 LLM Agent）；Agentic RL/GRPO 属 P-E（gated）。',
              '- 指纹排除属性 → role-drift 类漂移靠规则执行校验捕获（非指纹）；content-moved 规则 ok 但正文不完整（quality 揭示）。',
              '- LSH 为概率候选过滤；本小语料 definitive 聚簇用精确全对，LSH 召回实测见上。']
    return '\n'.join(lines) + '\n'


def render_ablation_report(results):
    lines = ['# P-C 特征模式敏感性消融（探索性 / 次要）', '',
             '> **诚实标注**：本消融是在预注册主运行（full-counts / 0.7 / complete-linkage，',
             '> 见 `outputs/pc.cluster_loop.v1`）观察到真实语料召回偏低之后**追加的 post-hoc 探索**，',
             '> 仅遍历既有 `dom_similarity.FEATURE_MODES` 六种特征模式；阈值 0.7、complete-linkage、',
             '> MinHash/LSH 参数与 seed 全部保持冻结，**不是阈值调参**。主结果仍以预注册的',
             '> full-counts 为准；本表用于解释"长度敏感 vs 存在性特征"对同模板聚簇的影响。', '',
             '零模型调用、零网络。仅真实语料（13 页）；合成 controlled 闭环保持主参数不变。', '',
             '| 模式 | 簇数 | 对精度 | 对召回 | ARI | sphinx-doc 最大同簇 | iana-help 最大同簇 | 派生次数 | 转移复用率 | 回退 |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for mode in sorted(results):
        r = results[mode]
        fam = r['family_summary']
        def biggest(g):
            cs = r['complete_linkage']['clusters']
            gids = set(fam[g]['members'])
            return max((len(gids & set(c)) for c in cs), default=0)
        pu, ru = r['cluster_purity'], r['rule_reuse']
        tag = '（预注册主模式）' if mode == PARAMS['feature_mode'] else ''
        lines.append('| %s%s | %d | %.4f | %.4f | %.4f | %d/5 | %d/3 | %d | %s | %d |' % (
            mode, tag, len(r['complete_linkage']['clusters']),
            pu['pair_precision'], pu['pair_recall'], pu['ari'],
            biggest('sphinx-documentation'), biggest('iana-help'),
            ru['rule_derivations'], str(ru['reuse_rate']), ru['fallback_count']))
    lines += ['', '## 解读边界', '',
              '- presence 类特征忽略段落/代码块数量差异（README 明示的同簇内差异），预期召回更高；',
              '  counts 类特征长度敏感，complete-linkage 下过分裂。这是特征选择的可解释影响，非数据泄漏。',
              '- 本消融不构成新的冻结协议；若未来采纳某模式，需走独立预注册 + 新校准语料，不得在本',
              '  development 语料上直接选优后宣称泛化。',
              '- 簇纯度≠提取准确率；复用率分母极小（见各模式 eligible_transfer_members），比值波动大。', '']
    return '\n'.join(lines) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description='P-C clustering + rule reuse closed loop (zero calls).')
    ap.add_argument('--real-manifest', type=Path,
                    default=ROOT / 'samples/dom_similarity.expanded_development.json')
    ap.add_argument('--controlled-manifest', type=Path,
                    default=ROOT / 'samples/dom_similarity.controlled.json')
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--ablation', action='store_true',
                    help='Secondary exploratory feature-mode sensitivity ablation (real corpus only; frozen threshold/linkage).')
    args = ap.parse_args(argv)
    out = Path(args.output)
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    if args.ablation:
        results = {}
        for mode in sorted(FEATURE_MODES):
            pages = load_pages(args.real_manifest, feature_mode=mode)
            results[mode] = run_corpus(pages, args.real_manifest,
                                       params={**PARAMS, 'feature_mode': mode})
        payload = {'tool_version': TOOL_VERSION, 'frozen_params': PARAMS,
                   'kind': 'post-hoc exploratory feature-mode sensitivity ablation (NOT threshold tuning)',
                   'primary_reference': 'outputs/pc.cluster_loop.v1 (pre-registered full-counts)',
                   'modes': results,
                   'note': 'Zero calls. Real corpus only. Purity != accuracy. See docs/P_C_CLUSTER_PLAN.md section 8.'}
        out.mkdir(parents=True)
        (out / 'pc_cluster_ablation.json').write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='')
        (out / 'PC_CLUSTER_ABLATION_REPORT.md').write_text(
            render_ablation_report(results), encoding='utf-8', newline='')
        summary = {m: {'clusters': len(r['complete_linkage']['clusters']),
                       'purity': r['cluster_purity'],
                       'reuse_rate': r['rule_reuse']['reuse_rate']}
                   for m, r in results.items()}
        print(json.dumps({'ablation': summary, 'output': str(out)}, ensure_ascii=False))
        return 0
    real = run_corpus(load_pages(args.real_manifest), args.real_manifest)
    controlled = run_corpus(load_pages(args.controlled_manifest), args.controlled_manifest,
                            expected_dir=ROOT / 'samples/drift_lab')
    result = {'tool_version': TOOL_VERSION, 'params': PARAMS,
              'corpora': {'real': real, 'controlled': controlled},
              'implementation_sha256': {p.name: sha(p.read_bytes()) for p in
                                        sorted((ROOT / 'src/webextractor').glob('dom_*.py')) +
                                        [ROOT / 'src/webextractor/rule_cache.py']},
              'note': 'Zero calls. Real/synthetic separate. Purity != accuracy. See docs/P_C_CLUSTER_PLAN.md.'}
    out.mkdir(parents=True)
    (out / 'pc_cluster_loop.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n',
                                              encoding='utf-8', newline='')
    (out / 'PC_CLUSTER_REPORT.md').write_text(render_report(result), encoding='utf-8', newline='')
    print(json.dumps({'real_clusters': real['complete_linkage']['clusters'],
                      'real_purity': real['cluster_purity'],
                      'real_reuse_rate': real['rule_reuse']['reuse_rate'],
                      'controlled_fallback': controlled['rule_reuse']['fallback_count'],
                      'output': str(out)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
