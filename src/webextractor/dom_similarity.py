"""Text-independent DOM path similarity for a small, labelled development corpus.

This is a deliberately simple structural baseline, not a production clustering
system. The default excludes all attributes, sibling indexes, URLs and text.
Optional feature ablations are explicit; only the semantic variant reads a
bounded ARIA role vocabulary. Inspect the pairwise report for each variant.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from itertools import combinations
import json
from pathlib import Path
import sys

from lxml import html


SKIP_TAGS = frozenset({'script', 'style', 'noscript', 'template'})
ROOT = Path(__file__).resolve().parents[2]
FEATURE_MODES = ('full-counts', 'full-presence', 'full-capped',
                 'suffix-presence', 'suffix-capped', 'semantic-presence')
COUNT_CAP = 3
SUFFIX_DEPTH = 3
SEMANTIC_ROLES = frozenset({'main', 'navigation', 'banner', 'contentinfo',
                            'complementary', 'article', 'region', 'search'})
TAG_ROLES = {'main': 'main', 'nav': 'navigation', 'aside': 'complementary',
             'article': 'article'}


def feature_settings(mode: str) -> dict:
    """Describe a fixed, named ablation without tuning it to a page pair."""
    if mode not in FEATURE_MODES:
        raise ValueError(f'Unknown feature mode: {mode}')
    settings = dict(mode=mode, path_scope='body-relative full tag path',
                    multiplicity='counts', ignored='all text, attributes, sibling indexes and head')
    if mode == 'full-presence':
        settings['multiplicity'] = 'presence (one per distinct path)'
    elif mode == 'full-capped':
        settings.update(multiplicity='capped counts', count_cap=COUNT_CAP)
    elif mode in {'suffix-presence', 'suffix-capped'}:
        settings.update(path_scope='suffix tag path', suffix_depth=SUFFIX_DEPTH,
                        multiplicity='presence (one per distinct suffix)')
        if mode == 'suffix-capped':
            settings.update(multiplicity='capped counts', count_cap=COUNT_CAP)
    elif mode == 'semantic-presence':
        settings.update(multiplicity='presence (one per distinct feature)',
                        ignored='all text, class, id, URLs, sibling indexes and head',
                        semantic_roles=sorted(SEMANTIC_ROLES),
                        semantic_source='main/nav/aside/article tags and bounded explicit ARIA roles')
    return settings


def structural_features(source: str | bytes, mode: str = 'full-counts') -> Counter[str]:
    """Compute a named structural variant; the default preserves v1 counts.

    A repeated path has multiplicity, so paragraph/list lengths affect the
    score. The body itself is not a feature. Empty documents yield no features.
    No extraction, noise lexicon, gold, network request or selected XPath is used.
    """
    feature_settings(mode)  # Validate even an empty document.
    if not source.strip():
        return Counter()
    document = html.document_fromstring(source, parser=html.HTMLParser(no_network=True))
    body = document.find('body')
    if body is None:
        return Counter()
    features: Counter[str] = Counter()

    def visit(node, path, role_context):
        if not isinstance(node.tag, str) or node.tag.lower() in SKIP_TAGS:
            return
        current = path + (node.tag.lower(),)
        key_path = current[-SUFFIX_DEPTH:] if mode.startswith('suffix-') else current
        features['/'.join(key_path)] += 1
        current_roles = role_context
        if mode == 'semantic-presence':
            explicit = next((role for role in node.get('role', '').lower().split()
                             if role in SEMANTIC_ROLES), None)
            role = explicit or TAG_ROLES.get(node.tag.lower())
            if role:
                current_roles += (role,)
            # Role-context features include descendants so changes to a body
            # landmark are visible beyond a single ancestor feature. Their
            # namespace cannot collide with ordinary tag paths.
            if current_roles:
                features['semantic:' + '/'.join(current_roles) + ':' + '/'.join(current)] += 1
        for child in node:
            visit(child, current, current_roles)

    for child in body:
        visit(child, (), ())
    if mode in {'full-presence', 'suffix-presence', 'semantic-presence'}:
        return Counter(dict.fromkeys(features, 1))
    if mode in {'full-capped', 'suffix-capped'}:
        return Counter({key: min(count, COUNT_CAP) for key, count in features.items()})
    return features


def multiset_jaccard(left: Counter[str], right: Counter[str]) -> float:
    """Sum of minimum path counts divided by sum of maximum path counts."""
    union = sum((left | right).values())
    return sum((left & right).values()) / union if union else 1.0


def connected_components(ids: list[str], scores: dict[tuple[str, str], float],
                         threshold: float) -> tuple[list[list[str]], list[dict]]:
    """Threshold edges, then flag non-clique components caused by chaining."""
    if not 0 <= threshold <= 1:
        raise ValueError('threshold must be between 0 and 1')
    adjacency = {page_id: set() for page_id in ids}
    for (left, right), score in scores.items():
        if score >= threshold:
            adjacency[left].add(right)
            adjacency[right].add(left)
    components = []
    remaining = set(ids)
    while remaining:
        pending = [min(remaining)]
        component = set()
        while pending:
            current = pending.pop()
            if current in component:
                continue
            component.add(current)
            pending.extend(adjacency[current] - component)
        remaining -= component
        components.append(sorted(component))
    chaining = []
    for component in components:
        below = []
        for left, right in combinations(component, 2):
            score = scores.get((left, right), scores.get((right, left)))
            if score is None or score < threshold:
                below.append(dict(left=left, right=right, score=score))
        if below:
            chaining.append(dict(component=component, below_threshold_pairs=below))
    return components, chaining


def run_manifest(manifest_path: Path, threshold: float, mode: str = 'full-counts') -> dict:
    """Load only development snapshots, validate hashes, report every input error."""
    variant_settings = feature_settings(mode)
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    if not 0 <= threshold <= 1:
        raise ValueError('threshold must be between 0 and 1')
    registry_path = ROOT / 'samples/sample_registry.json'
    reserved_hashes = set()
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding='utf-8-sig'))
        reserved_hashes = {case['html_sha256'] for case in registry['cases']
                           if case.get('current_role', '').startswith('validation')}
    pages, errors, seen = [], [], set()
    for page in manifest['pages']:
        try:
            page_id = page['id']
            if not isinstance(page_id, str) or not page_id or page_id in seen:
                raise ValueError('Page ids must be unique nonempty strings')
            seen.add(page_id)
            if page.get('split') != 'development':
                raise ValueError('Only development snapshots are accepted')
            # Compare the declared hash before even opening a known validation
            # file; changing a manifest split does not release a held-out page.
            if page.get('sha256', '').lower() in reserved_hashes:
                raise ValueError('Snapshot inventory marks this page as validation')
            if page['source_kind'] not in {'real', 'synthetic'}:
                raise ValueError('source_kind must be real or synthetic')
            if not isinstance(page['manual_group'], str) or not page['manual_group']:
                raise ValueError('A nonempty manual_group is required')
            path = manifest_path.parent / page['html']
            payload = path.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            if digest != page['sha256'].lower():
                raise ValueError('Snapshot SHA256 mismatch')
            features = structural_features(payload, mode)
            if not features:
                raise ValueError('No structural body features; cannot infer template')
            pages.append(dict(id=page_id, manual_group=page['manual_group'],
                              source_kind=page['source_kind'], html_sha256=digest,
                              features=features, distinct_paths=len(features),
                              total_paths=sum(features.values())))
        except Exception as error:
            errors.append(dict(id=page.get('id'), error=f'{type(error).__name__}: {error}'))
    scores, pairs = {}, []
    for left, right in combinations(pages, 2):
        score = multiset_jaccard(left['features'], right['features'])
        same = left['manual_group'] == right['manual_group']
        scores[left['id'], right['id']] = score
        pairs.append(dict(left=left['id'], right=right['id'], score=score,
                          same_manual_group=same, threshold_edge=score >= threshold,
                          source_kinds=[left['source_kind'], right['source_kind']]))
    components, chaining = connected_components([p['id'] for p in pages], scores, threshold)
    memberships = {page_id: index for index, component in enumerate(components) for page_id in component}
    false_merges, false_splits = [], []
    for pair in pairs:
        grouped = memberships[pair['left']] == memberships[pair['right']]
        pair['same_predicted_component'] = grouped
        if grouped and not pair['same_manual_group']:
            false_merges.append(dict(pair))
        if not grouped and pair['same_manual_group']:
            false_splits.append(dict(pair))
    return dict(manifest=str(manifest_path),
                manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                settings=dict(variant_settings,
                              feature='body-relative full tag-path multiset' if mode == 'full-counts' else mode,
                              skipped_tags=sorted(SKIP_TAGS), metric='multiset Jaccard',
                              threshold=threshold, clustering='threshold-edge connected components'),
                pages=pages, pairs=pairs, components=components, chaining_warnings=chaining,
                false_merge_pairs=false_merges, false_split_pairs=false_splits, errors=errors,
                note='Manual groups are source-reviewed template hypotheses, not extractor-quality labels. '
                     'Synthetic and real pairs are labelled separately; do not aggregate as real-site accuracy. '
                     'Connected components can chain below-threshold pairs. No threshold is learned or tuned here.')


def render_report(report: dict) -> str:
    lines = ['# DOM结构相似度原型', '',
             f"显式阈值：{report['settings']['threshold']}；特征模式：{report['settings'].get('mode', 'full-counts')}。", '',
             '固定特征设置：`' + json.dumps(report['settings'], ensure_ascii=False) + '`', '',
             '| 页面对 | 相似度 | 人工同组 | 阈值连边 | 最终同簇 | 样本类型 |',
             '| --- | ---: | --- | --- | --- | --- |']
    for pair in report['pairs']:
        lines.append(f"| {pair['left']} / {pair['right']} | {pair['score']:.4f} | "
                     f"{pair['same_manual_group']} | {pair['threshold_edge']} | "
                     f"{pair['same_predicted_component']} | {'/'.join(pair['source_kinds'])} |")
    lines.extend(['', '连通分量：' + json.dumps(report['components'], ensure_ascii=False), '',
                  f"误聚页面对：{len(report['false_merge_pairs'])}；漏聚页面对：{len(report['false_split_pairs'])}。", '',
                  '这是标签结构基线；模板分组不保证同一XPath可复用，也不保证正文完整。阈值应在验证前冻结；站点公共外壳与包装层可能主导分数。'])
    for warning in report['chaining_warnings']:
        lines.extend(['', '链式聚簇警告：' + json.dumps(warning, ensure_ascii=False)])
    for error in report['errors']:
        lines.extend(['', '输入错误：' + json.dumps(error, ensure_ascii=False)])
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Compare development DOM structures without page text')
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--threshold', type=float, required=True)
    parser.add_argument('--feature-mode', choices=FEATURE_MODES, default='full-counts',
                        help='Fixed feature ablation; defaults to the historical v1 multiset')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() == args.report.resolve():
        parser.error('JSON and Markdown outputs must differ')
    if args.output.exists() or args.report.exists():
        parser.error('Output exists; choose new filenames to preserve earlier experiments')
    try:
        result = run_manifest(args.manifest, args.threshold, args.feature_mode)
    except (ValueError, OSError, KeyError) as error:
        parser.error(str(error))
    for path in (args.output, args.report):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    args.report.write_text(render_report(result), encoding='utf-8')
    print(args.report)
    return int(bool(result['errors']))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
