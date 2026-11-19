"""Run predeclared development ablations, preserving earlier reports."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.webextractor.dom_similarity import run_manifest, render_report

MODES = ('full-counts', 'full-presence', 'full-capped', 'semantic-presence', 'suffix-capped')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    target = args.output_dir.resolve()
    if target.exists() and any(target.iterdir()):
        parser.error('Choose an empty output directory; previous experiments are immutable')
    target.mkdir(parents=True, exist_ok=True)
    protocol = ROOT / 'docs/CLUSTER_ABLATION_PROTOCOL.md'
    rows = []
    for corpus, filename in [('real', 'dom_similarity.expanded_development.json'),
                             ('controlled', 'dom_similarity.controlled.json')]:
        for mode in MODES:
            report = run_manifest(ROOT / 'samples' / filename, 0.7, mode)
            if report['errors']:
                raise RuntimeError(report['errors'])
            stem = corpus + '.' + mode
            (target / (stem + '.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
            (target / (stem + '.md')).write_text(render_report(report), encoding='utf-8')
            positive = sum(p['same_manual_group'] for p in report['pairs'])
            rows.append(dict(corpus=corpus, mode=mode, pages=len(report['pages']),
                pairs=len(report['pairs']), positive_pairs=positive,
                negative_pairs=len(report['pairs'])-positive,
                false_merges=len(report['false_merge_pairs']),
                false_splits=len(report['false_split_pairs']),
                components=len(report['components']),
                chaining_components=len(report['chaining_warnings']),
                manifest_sha256=report['manifest_sha256'],
                implementation_sha256=report['implementation_sha256']))
    summary = dict(threshold=0.7, modes=MODES,
        protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(), rows=rows,
        note='Development only. Real and synthetic denominators separate; errors use final components.')
    (target / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['# 固定阈值DOM特征对照', '',
        '阈值0.7；误聚/漏聚按最终连通分量统计；真实与合成分开。', '',
        '| 语料 | 模式 | 页数 | 同组/异组页面对 | 误聚 | 漏聚 | 簇数 | 链式分量 |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in rows:
        lines.append(f"| {r['corpus']} | {r['mode']} | {r['pages']} | {r['positive_pairs']}/{r['negative_pairs']} | {r['false_merges']} | {r['false_splits']} | {r['components']} | {r['chaining_components']} |")
    lines += ['', '固定来源、人工分组及特征设置均见逐模式JSON；当前集合没有独立聚簇验证成绩。', '']
    (target / 'summary.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
