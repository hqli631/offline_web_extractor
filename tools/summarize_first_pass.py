"""Summarize preserved evaluations without changing annotations or predictions."""
import argparse
from collections import Counter
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('reports', nargs='+', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    lines = ['# 首轮错误诊断', '',
             '只读取已保存报告；块文本比较不检查顺序或类型，差异数量不等于丢失的文字数量。', '',
             '| 页面 | 标题一致 | 预测/标准块 | 文本精确率 | 文本召回率 | 结构全匹配 |',
             '| --- | --- | --- | --- | --- | --- |']
    details = []
    for path in args.reports:
        report = json.loads(path.read_text(encoding='utf-8-sig'))
        predicted = report['predicted']['blocks']
        expected = report['expected']['blocks']
        p = Counter(b['text'] for b in predicted)
        e = Counter(b['text'] for b in expected)
        precision = report['block_text_precision']
        recall = report['block_text_recall']
        lines.append(f'| {path.stem} | {report["title_exact"]} | {len(predicted)}/{len(expected)} | {precision:.4f} | {recall:.4f} | {report["blocks_exact"]} |')
        details.extend(['', f'## {path.stem}', '', f'原始报告：{path.as_posix()}', '',
                        '预测类型：' + json.dumps(dict(Counter(b['kind'] for b in predicted)), ensure_ascii=False), '',
                        '标准类型：' + json.dumps(dict(Counter(b['kind'] for b in expected)), ensure_ascii=False)])
        for label, difference in [('多提/拆分不一致', p-e), ('漏匹配/拆分不一致', e-p)]:
            details.extend(['', f'### {label}（{sum(difference.values())}块）', ''])
            for value, count in difference.items():
                details.append(f'> {count}次：' + value.replace('\n', ' '))
                details.append('')
        typed_p = Counter((b['kind'], b['text']) for b in predicted)
        typed_e = Counter((b['kind'], b['text']) for b in expected)
        details.extend(['', f'类型+文本交集：{sum((typed_p & typed_e).values())}块；仍不检查顺序、层级和列表编号。'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text('\n'.join(lines + details) + '\n', encoding='utf-8')
    print(args.output)


if __name__ == '__main__':
    main()
