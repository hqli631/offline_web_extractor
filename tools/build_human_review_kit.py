# -*- coding: utf-8 -*-
"""P0 human-calibration kit builder (blind pass).

Renders per-case blind review packets and a label template from the frozen
node-4 batch. Blind packets contain ONLY task inputs (registered source nodes,
candidate, optional gold) plus the rubrics quick reference. They never contain
mutation types, silver expectations, judge assessments or program scores.

Fails closed on freeze drift; refuses to overwrite an existing output dir.
No network, no model calls, deterministic output bytes.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.score_judge_results import DIMS, check_freeze, load_json, sha256_bytes

KIT_VERSION = '1.0.0'

DIM_ZH = {
    'completeness': '完整性',
    'cleanliness': '纯净度',
    'structure': '结构',
    'title': '标题忠实性',
    'format': '格式（仅代码块）',
}

QUICK_REF = """\
### 分数锚点（0-4 整数）
| 分数 | 含义 |
| --- | --- |
| 4 | 几乎完全符合（程序参考比例>=0.98；语义上无明显问题） |
| 3 | 小比例差异（>=0.90） |
| 2 | 明显差异（>=0.70） |
| 1 | 大幅差异（>=0.40） |
| 0 | 大部分不符合（<0.40） |
比例仅是参考，语义判断以你看到的证据为准；无法量化时按差异程度给分并在 note 说明。

### 状态 status
- scored：证据充分，正常评分。
- partial：证据不完整（如源被截断）仍可给分，但置信度低。
- unscored：无法判断，score 填 null。
- not_applicable：维度不适用（如无代码时的格式维），score 填 null。

### 严重度 severity
- none：无问题。
- minor：轻微（如标题仅丢章节编号、少量未对齐差异）。
- major：严重（结构属性不符、段落乱序、代码缩进/换行错误、噪声超额混入、非编号类标题差异、大段缺失）。
- critical：空候选。
- unknown：证据不足无法定级。

### 决策 decision
- fail：存在 major/critical 问题。
- uncertain：无严重问题但有其他问题，或存在 partial/unscored。
- pass：各维均无问题且证据充分。
- source_only（无参考答案）：只能 uncertain 或 fail，不得 pass。

### 其他规则
- 网页文本中的指令是数据，不是命令；候选若服从了页面内嵌指令属于错误。
- score 为整数时 status 必须是 scored/partial；score 为 null 时 status 必须是 unscored/not_applicable。
- 每个维度都必须填 severity；note 可选（简短中文）。
"""


def write_text(path, text):
    Path(path).write_text(text, encoding='utf-8', newline='')


def ordered_cases(batch):
    return sorted(batch['cases'],
                  key=lambda r: (0 if r['split'] == 'development' else 1, r['case_id']))


def _fmt_attrs(block):
    parts = []
    for key in ('kind', 'heading_level', 'list_type', 'depth', 'ordinal', 'footnote_label'):
        if key in block and block[key] is not None:
            parts.append('%s=%s' % (key, block[key]))
    return ' '.join(parts)


def render_blocks(title_ref, title, blocks):
    lines = ['标题 `%s`：%s' % (title_ref, title), '']
    for b in blocks:
        lines.append('#### `%s` %s' % (b['ref'], _fmt_attrs(b)))
        lines.append('')
        lines.append(b.get('text') or '（空文本）')
        lines.append('')
    return '\n'.join(lines)


def render_source(source):
    lines = []
    if source.get('truncated'):
        lines.append('> **注意：源证据被截断**。未展示部分不可当作"缺失"的证据；相关维度请标 partial，decision 不得 pass。')
        lines.append('')
    for node in source.get('nodes') or []:
        lines.append('#### `%s` <%s> %s' % (node['ref'], node.get('tag', ''), node.get('xpath', '')))
        lines.append('')
        lines.append(node.get('text') or '（空文本）')
        lines.append('')
    return '\n'.join(lines)


def blind_codes(rows):
    return {row['case_id']: 'B%02d' % i for i, row in enumerate(rows, 1)}


def render_blind_packet(case_row, index, total, code):
    meta = case_row.get('case_meta') or {}
    report = case_row.get('report') or {}
    prompt = report.get('prompt') or {}
    mode = meta.get('mode') or report.get('mode')
    source = prompt.get('source') or {}
    candidate = prompt.get('candidate') or {}
    gold = prompt.get('gold')
    lines = [
        '# 盲评案卷 %s' % code,
        '',
        '- 序号：%d / %d' % (index, total),
        '- split：%s' % case_row['split'],
        '- 模式：%s' % mode,
        '- 源截断：%s' % ('是' if source.get('truncated') else '否'),
        '',
        '## 评分速查（Rubrics v2 摘要）',
        '',
        QUICK_REF,
        '',
        '## 候选提取结果（p: 引用）',
        '',
        render_blocks(candidate.get('title_ref', 'p:title'), candidate.get('title', ''),
                      candidate.get('blocks') or []),
        '',
    ]
    if mode == 'with_gold' and gold:
        lines += ['## 参考答案（g: 引用）', '',
                  render_blocks(gold.get('title_ref', 'g:title'), gold.get('title', ''),
                                gold.get('blocks') or []), '']
    else:
        lines += ['## 参考答案', '',
                  '本例为 source_only：无参考答案。仅依据源证据判断；decision 只能 uncertain/fail。', '']
    lines += ['## 网页源证据（s: 引用，与 judge 所见完全一致）', '', render_source(source), '',
              '## 填写入口', '',
              '打开同目录 `human_labels.blind.json`，找到 `blind_code` 为 `%s` 的条目，填写 decision 与五个维度，保存。' % code,
              '本案卷不含任何 judge/silver/程序分数；填写前请勿查阅其他输出文件，避免锚定。', '']
    text = '\n'.join(lines)
    if case_row['case_id'] in text:
        raise ValueError('blind packet leaks case id: %s' % case_row['case_id'])
    return text


def build_template(batch, codes):
    cases = []
    for row in ordered_cases(batch):
        meta = row.get('case_meta') or {}
        cases.append({
            'blind_code': codes[row['case_id']], 'split': row['split'], 'mode': meta.get('mode'),
            'decision': None,
            'dimensions': {n: {'score': None, 'status': None, 'severity': None, 'note': ''}
                           for n in DIMS},
            'overall_note': '',
        })
    return {'label_version': 1, 'stage': 'blind', 'annotator': '', 'annotation_date': '',
            'instructions': '逐案填写：decision 取 pass/uncertain/fail；score 为 0-4 整数或 null；'
                            'status/severity 规则见案卷速查；source_only 不得 pass。'
                            '全部案例填完后运行 ingest --stage blind。',
            'cases': cases}


def render_index(rows, out_dir, codes):
    dev = [codes[r['case_id']] for r in rows if r['split'] == 'development']
    test = [codes[r['case_id']] for r in rows if r['split'] == 'frozen_test']
    lines = [
        '# P0 人工校准 · 盲评阶段索引',
        '',
        '共 %d 例（development %d / frozen_test %d）。预计总耗时 1.5-2.5 小时，可分两次完成。' % (len(rows), len(dev), len(test)),
        '',
        '## 工作流',
        '1. 按顺序阅读 `packets/<blind_code>.md` 案卷（候选 + 参考答案 + 源证据 + 评分速查）。',
        '2. 在 `human_labels.blind.json` 对应条目填写 decision 与五维 score/status/severity。',
        '3. 先填 annotator（你的标识）与 annotation_date（YYYY-MM-DD）。',
        '4. 全部填完后运行校验与一致性计算（见下），把输出发回给助手。',
        '',
        '## 建议分会话',
        '- 会话1（development，%d 例）：%s' % (len(dev), ', '.join(dev)),
        '- 会话2（frozen_test，%d 例）：%s' % (len(test), ', '.join(test)),
        '',
        '## 盲评纪律',
        '- 填写前不要查看 outputs/ 下的 judge 批量结果、metrics、silver 标签或本报告以外的文档。',
        '- 案卷以中性编号 B01-B23 标识，已隐藏真实案例名、变异类型与所有机器分数。',
        '- `sealed_mapping.json` 是编号到案例名的密封映射：盲评阶段禁止打开（裁决阶段才需要）。',
        '- 拿不准就标 unscored/unknown 并写 note，不要猜。',
        '',
        '## 填完后运行（项目根目录）',
        '```',
        'python -m tools.ingest_human_labels --stage blind --labels "%s" --output outputs/human_review/round1.v1' % (out_dir / 'human_labels.blind.json'),
        '```',
        '校验失败会列出全部错误条目；修正后重跑（输出目录需换新名或先移走旧目录）。',
        '',
    ]
    return '\n'.join(lines)


def build_kit(args):
    out = Path(args.output)
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    batch = load_json(args.batch)
    stability = load_json(args.stability)
    freeze = load_json(args.freeze)
    problems = check_freeze(batch, stability, freeze, args.manifest)
    if problems:
        print(json.dumps({'error': 'freeze_integrity', 'problems': problems}, ensure_ascii=False))
        return 2
    rows = ordered_cases(batch)
    codes = blind_codes(rows)
    out.mkdir(parents=True)
    (out / 'packets').mkdir()
    rels = []
    for i, row in enumerate(rows, 1):
        code = codes[row['case_id']]
        rel = 'packets/%s.md' % code
        write_text(out / rel, render_blind_packet(row, i, len(rows), code))
        rels.append(rel)
    for rel, text in (
            ('human_labels.blind.json',
             json.dumps(build_template(batch, codes), ensure_ascii=False, indent=2) + '\n'),
            ('sealed_mapping.json',
             json.dumps({codes[r['case_id']]: r['case_id'] for r in rows},
                        ensure_ascii=False, indent=2) + '\n'),
            ('INDEX.md', render_index(rows, out, codes))):
        write_text(out / rel, text)
        rels.append(rel)
    kit_manifest = {
        'kit_version': KIT_VERSION,
        'inputs': {name: sha256_bytes(Path(getattr(args, name)).read_bytes())
                   for name in ('batch', 'stability', 'freeze', 'manifest')},
        'n_cases': len(rows),
        'files': {rel: sha256_bytes((out / rel).read_bytes()) for rel in sorted(rels)},
    }
    write_text(out / 'kit_manifest.json',
               json.dumps(kit_manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output': str(out), 'n_cases': len(rows),
                      'development': sum(1 for r in rows if r['split'] == 'development'),
                      'frozen_test': sum(1 for r in rows if r['split'] == 'frozen_test')},
                     ensure_ascii=False))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', type=Path,
                        default=ROOT / 'outputs' / 'rubrics_judge.node4.batch.v6.json')
    parser.add_argument('--stability', type=Path,
                        default=ROOT / 'outputs' / 'rubrics_judge.node4.stability.v1.json')
    parser.add_argument('--freeze', type=Path,
                        default=ROOT / 'outputs' / 'rubrics_judge.node3.freeze.v2.json')
    parser.add_argument('--manifest', type=Path,
                        default=ROOT / 'samples' / 'calibration_manifest.json')
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'outputs' / 'human_review' / 'blind.v2')
    args = parser.parse_args(argv)
    return build_kit(args)


if __name__ == '__main__':
    sys.exit(main())
