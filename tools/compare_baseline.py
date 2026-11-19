"""Compare local extractor and Trafilatura on frozen development HTML.

No URL fetch, no tuning, no production rules or reference rewriting. Run using
.baseline-venv/Scripts/python.exe to place both methods in the same environment.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from difflib import SequenceMatcher
import hashlib
from importlib.metadata import distributions, version
import json
from pathlib import Path
import platform
import re
from statistics import median
import sys
from time import perf_counter_ns

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SETTINGS = dict(fast=False, no_fallback=False, favor_precision=False,
                favor_recall=False, include_comments=False, include_tables=True,
                include_images=False, include_formatting=False, include_links=False,
                deduplicate=False, with_metadata=True, output_format='python')
BLOCK_TAGS = {'head', 'p', 'quote', 'list', 'item', 'code', 'table', 'row', 'cell', 'div', 'body'}


def normalize(value):
    return ' '.join(value.split())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def blocks_text(blocks, title=''):
    parts = []
    removed = 0
    for block in blocks:
        text = block['text']
        if block['kind'] == 'heading' and title and normalize(text) == normalize(title):
            removed += 1
            continue
        # A table block stores serialization separators not present in source prose.
        if block['kind'] == 'table':
            text = text.replace(' | ', ' ')
        parts.append(text)
    return normalize('\n'.join(parts)), removed


def baseline_text(body, title):
    body = deepcopy(body)
    removed = 0
    for head in body.xpath('.//head'):
        if title and normalize(''.join(head.itertext())) == normalize(title):
            parent = head.getparent()
            if parent is not None:
                # Extracted XML heading tails are usually whitespace; preserve them.
                tail = head.tail or ''
                previous = head.getprevious()
                if previous is None:
                    parent.text = (parent.text or '') + tail
                else:
                    previous.tail = (previous.tail or '') + tail
                parent.remove(head)
                removed += 1

    def read(node):
        pieces = [node.text or '']
        for child in node:
            boundary = child.tag in BLOCK_TAGS
            if boundary:
                pieces.append('\n')
            pieces.append(read(child))
            if boundary:
                pieces.append('\n')
            pieces.append(child.tail or '')
        return ''.join(pieces)

    return normalize(read(body)), removed


def content_metrics(predicted, expected):
    matched = sum((Counter(predicted) & Counter(expected)).values())
    precision = matched / len(predicted) if predicted else float(not expected)
    recall = matched / len(expected) if expected else float(not predicted)
    # CJK characters individually, Latin words and punctuation individually.
    token_pattern = r'[\u3400-\u9fff]|[A-Za-z0-9_]+|[^\s]'
    p_tokens = re.findall(token_pattern, predicted)
    e_tokens = re.findall(token_pattern, expected)
    order_ratio = SequenceMatcher(None, e_tokens, p_tokens, autojunk=False).ratio()
    return dict(char_precision=precision, char_recall=recall,
                char_f1=2*precision*recall/(precision+recall) if precision+recall else 0.0,
                ordered_token_similarity=order_ratio,
                normalized_text_exact=predicted == expected,
                predicted_chars=len(predicted), expected_chars=len(expected))


def timed_call(function, source, repetitions):
    function(source)  # One warmup, not included in measured samples.
    elapsed = []
    output = None
    for _ in range(repetitions):
        start = perf_counter_ns()
        output = function(source)
        elapsed.append((perf_counter_ns() - start) / 1_000_000)
    return output, dict(unit='ms', warmup=1, repetitions=repetitions,
                        samples=elapsed, median=median(elapsed),
                        scope='HTML bytes parse + extraction; excludes file I/O, imports, projection and metrics')


def render(report):
    lines = ['# 静态基线对比', '',
             '同一HTML、同一Python环境；文本指标使用全部正文块。耗时为预热后串行中位数，不能推算工业吞吐。', '',
             '| 页面 | 方法 | 状态 | 字符P | 字符R | 有序相似度 | 标题一致 | 中位耗时ms |',
             '| --- | --- | --- | ---: | ---: | ---: | --- | ---: |']
    for case in report['cases']:
        for name, result in case['methods'].items():
            if 'error' in result:
                lines.append(f'| {case["id"]} | {name} | error | — | — | — | — | — |')
            else:
                m = result['metrics']
                lines.append(f'| {case["id"]} | {name} | {result["status"]} | {m["char_precision"]:.4f} | {m["char_recall"]:.4f} | {m["ordered_token_similarity"]:.4f} | {result["title_exact"]} | {result["timing"]["median"]:.3f} |')
    lines.extend(['', '## 比较边界', '',
                  '- 字符次数交集忽略顺序；有序相似度基于词/字元SequenceMatcher，属于诊断相似度，不是精确编辑距离或事实正确率。',
                  '- 代码空白、列表编号、表格分隔符和Markdown标记不参与文本比较；结构指标仅生产结果对自身协议计算，Trafilatura结构指标为空，不能冒充同构评测。',
                  '- 标题从正文投影剔除：仅移除与各方法自己预测标题相等的heading，不用标准答案修正预测。原始输出和移除计数保存在JSON。',
                  '- 统一协议选择和剩余标注差异见 manifest 与 docs/BASELINE_PROTOCOL.md。开发页结果不等于未见站点泛化。'])
    for case in report['cases']:
        for name, result in case['methods'].items():
            if 'error' in result:
                lines.extend(['', f'错误 {case["id"]}/{name}：{result["error"]}'])
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--repetitions', type=int, default=5)
    args = parser.parse_args()
    if args.repetitions < 3:
        parser.error('At least 3 measured repetitions required')
    if args.output.exists() or args.report.exists():
        parser.error('Output exists; use a new filename to preserve prior experiments')
    import trafilatura
    from lxml import etree
    from src.webextractor.extractor import extract_html
    if version('trafilatura') != '2.0.0':
        parser.error('Protocol v1 requires trafilatura==2.0.0; install requirements-baseline.txt')
    manifest = json.loads(args.manifest.read_text(encoding='utf-8-sig'))
    if any(c.get('split') != 'development' for c in manifest['cases']):
        parser.error('This runner only accepts development cases; reserved validation is not authorized here')
    registry_path = ROOT / 'samples/sample_registry.json'
    registry = json.loads(registry_path.read_text(encoding='utf-8')) if registry_path.exists() else {'cases': []}
    reserved = {c['html'] for c in registry['cases'] if c.get('current_role') == 'validation_reserved'}
    if any(c['html'] in reserved for c in manifest['cases']):
        parser.error('Manifest includes a reserved validation snapshot, even if mislabeled development')
    source_hashes = {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p)
                     for p in sorted((ROOT/'src/webextractor').glob('*.py'))}
    report = dict(manifest=str(args.manifest.resolve()), manifest_sha256=sha(args.manifest),
                  runner_sha256=sha(Path(__file__)),
                  baseline_protocol_sha256=sha(ROOT/'docs/BASELINE_PROTOCOL.md'),
                  baseline_requirements_sha256=sha(ROOT/'requirements-baseline.txt'),
                  environment=dict(python=sys.version, executable=sys.executable,
                                   platform=platform.platform(), processor=platform.processor(),
                                   packages={d.metadata['Name']: d.version for d in distributions()}),
                  trafilatura_settings=SETTINGS, source_sha256=source_hashes,
                  protocol='all-block text v1; title separated; explicit content-only projection; serial warmed timing',
                  cases=[])
    for case in manifest['cases']:
        row = dict(id=case['id'], split=case['split'], methods={})
        report['cases'].append(row)
        try:
            source_path = args.manifest.parent / case['html']
            expected_path = args.manifest.parent / case['expected']
            payload = source_path.read_bytes()
            if sha(source_path) != case['sha256']:
                raise ValueError('HTML hash mismatch')
            expected = json.loads(expected_path.read_text(encoding='utf-8-sig'))
            expected_text, _ = blocks_text(expected['blocks'])
            row.update(html_sha256=sha(source_path), expected_sha256=sha(expected_path),
                       expected_body_text=expected_text, expected_title=expected['title'])
        except Exception as error:
            row['methods']['input'] = dict(error=f'{type(error).__name__}: {error}')
            continue
        # Alternate order by case index to reduce a fixed order advantage.
        names = ['rules', 'trafilatura'] if len(report['cases']) % 2 else ['trafilatura', 'rules']
        for name in names:
            try:
                if name == 'rules':
                    result, timing = timed_call(extract_html, payload, args.repetitions)
                    raw = result.to_dict()
                    title = result.title
                    text, removed = blocks_text(raw['blocks'], title)
                    status = result.status
                    structure_exact = raw['blocks'] == expected['blocks']
                else:
                    function = lambda data: trafilatura.bare_extraction(data, **SETTINGS)
                    result, timing = timed_call(function, payload, args.repetitions)
                    if result is None or result.body is None:
                        title, text, removed, status, raw = '', '', 0, 'empty_body', None
                    else:
                        title = result.title or ''
                        text, removed = baseline_text(result.body, title)
                        status = 'ok' if text else 'empty_body'
                        raw = dict(title=title, body_xml=etree.tostring(result.body, encoding='unicode'))
                    structure_exact = None
                row['methods'][name] = dict(status=status, title=title, title_exact=title == expected['title'],
                                            body_text=text, title_headings_removed=removed,
                                            metrics=content_metrics(text, expected_text),
                                            blocks_exact=structure_exact, timing=timing, raw=raw)
            except Exception as error:
                row['methods'][name] = dict(error=f'{type(error).__name__}: {error}')
    after = {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p)
             for p in sorted((ROOT/'src/webextractor').glob('*.py'))}
    if after != source_hashes:
        parser.error('Production source changed during experiment; no report saved. Rerun after source freeze.')
    for path in (args.output, args.report):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    args.report.write_text(render(report), encoding='utf-8')
    print(args.report)
    return int(any('error' in m for c in report['cases'] for m in c['methods'].values()))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
