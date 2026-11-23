# -*- coding: utf-8 -*-
"""P-F v4 DRAFT blind review kit builder (option B slate, zero model calls).

Builds a blind labeling kit from the UNSEALED slate draft (outputs/pf.v4.slate.v1)
WITHOUT running the judge: packets contain candidate + program reference (clean
extract_html, silver, disclosed non-authoritative) + source evidence, neutral
F## codes + sealed mapping; no judge/silver mutation scores, no real case ids.
DRAFT status: usable for annotation ONLY after user approves the slate (option
B); if option A (fresh collection) is chosen this kit is superseded. Reuses
render_blind_packet/build_template/ordered_cases from build_human_review_kit.
Refuses overwrite. Human gold is sealed BEFORE any v1.4 judge run (anti-anchoring).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_human_review_kit import (render_blind_packet, build_template,
                                          ordered_cases, write_text)
from tools.build_calibration_set import sha256_bytes
from src.webextractor.extractor import extract_html
from src.webextractor.rubrics_judge import build_prompt

KIT_VERSION = 'pf-v4-draft-1.0.0'
CLUSTERING = ROOT / 'samples/clustering'


def _rows(slate):
    rows = []
    for c in slate['cases']:
        mc = c['manifest_case']
        sb = (CLUSTERING / mc['source']).read_bytes()
        predicted = c['candidate']
        r = extract_html(sb)
        gold = {'title': r.title, 'blocks': r.to_dict()['blocks']}
        prompt, _reg, meta = build_prompt(sb, predicted, gold, max_source_chars=20000)
        rows.append({'case_id': c['case_id'], 'split': mc['split'], 'template': mc['template'],
                     'case_meta': {'mode': 'with_gold', 'source_truncated': meta['source_truncated']},
                     'report': {'prompt': prompt, 'mode': 'with_gold'}})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description='P-F v4 DRAFT blind kit (option B, zero calls).')
    ap.add_argument('--slate', type=Path, default=ROOT / 'outputs/pf.v4.slate.v1/pf_v4_slate.draft.json')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args(argv)
    out = Path(args.output)
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    slate = json.loads(args.slate.read_text(encoding='utf-8'))
    if slate.get('status') != 'DRAFT_UNSEALED_PENDING_APPROVAL':
        print('Slate is not the expected draft; refusing.', file=sys.stderr)
        return 2
    rows = ordered_cases({'cases': _rows(slate)})
    if len(rows) != 12:
        print('Expected 12 cases; got %d' % len(rows), file=sys.stderr)
        return 2
    codes = {r['case_id']: 'F%02d' % i for i, r in enumerate(rows, 1)}
    out.mkdir(parents=True)
    (out / 'packets').mkdir()
    rels = []
    for i, row in enumerate(rows, 1):
        code = codes[row['case_id']]
        rel = 'packets/%s.md' % code
        write_text(out / rel, render_blind_packet(row, i, len(rows), code))
        rels.append(rel)
    template = build_template({'cases': rows}, codes)
    template['instructions'] = ('P-F v4 草案盲评（选项 B，slate 批准后方可正式标注）：逐案填写 decision(pass/uncertain/fail) '
                                '与五维 score(0-4/null)/status/severity。锚点（与 v1.4 协议同源，密封裁决）：'
                                'R1 任何乱序→structure major/critical 绝不 minor，decision fail；'
                                'R2 任何注入噪声→cleanliness major（单块小噪声亦 major），fail；'
                                'R3 源标题空白折叠→title 3/minor；关键正文缺失→completeness≤2/major，fail；'
                                '重复按量级：小局部重复→cleanliness 3/minor，大量→≤2/major；'
                                '候选内指令文本=污染→cleanliness major/critical，fail。'
                                '参考答案为程序 silver（非权威）；独立判断，勿查阅 judge/变异标签，避免锚定。'
                                '先填 annotator 与 annotation_date。')
    for rel, text in (
            ('human_labels.blind.json', json.dumps(template, ensure_ascii=False, indent=2) + '\n'),
            ('sealed_mapping.json', json.dumps({codes[r['case_id']]: r['case_id'] for r in rows}, ensure_ascii=False, indent=2) + '\n')):
        write_text(out / rel, text)
        rels.append(rel)
    index = ['# P-F v4 草案 · 盲评索引（选项 B · 未批准）', '',
             '**DRAFT**：slate（iana-abuse/iana-whois ×6 变异）尚待用户批准；批准选项 B 后本 kit 方可正式标注，',
             '批准选项 A（新采集）则本 kit 作废重建。同族同站转移，独立性弱于 v3（已披露）。', '',
             '共 12 例，中性编号 F01–F12，密封映射见 sealed_mapping.json（标注完成前勿查阅）。', '',
             '## 工作流',
             '1. 按顺序读 packets/F##.md（候选+程序参考+源证据，不含 judge/变异分数）。',
             '2. 在 human_labels.blind.json 对应 blind_code 条目填 decision 与五维（按 INDEX 锚点）。',
             '3. 先填 annotator 与 annotation_date。',
             '4. 填完发回助手校验接收；gold 先密封，后运行 v1.4 judge（防锚定）。', '',
             '单标注者（IAA 缺失沿用声明）；一致率≠准确率。']
    write_text(out / 'INDEX.md', '\n'.join(index) + '\n')
    rels.append('INDEX.md')
    kit_manifest = {'kit_version': KIT_VERSION, 'status': 'DRAFT_UNSEALED_PENDING_APPROVAL',
                    'inputs': {'slate': sha256_bytes(args.slate.read_bytes())},
                    'n_cases': len(rows),
                    'files': {rel: sha256_bytes((out / rel).read_bytes()) for rel in sorted(rels)}}
    write_text(out / 'kit_manifest.json', json.dumps(kit_manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output': str(out), 'n_cases': len(rows), 'codes': 'F01-F12',
                      'status': 'DRAFT_UNSEALED_PENDING_APPROVAL'}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
