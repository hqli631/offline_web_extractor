# -*- coding: utf-8 -*-
"""P-F v4 slate DRAFT builder (option B, zero model calls, zero network).

Builds a 12-case PROPOSAL slate (2 templates x 6 variants, v3 shape) from two
never-judge-exposed short real snapshots (<=20k chars, no truncation):
iana-abuse, iana-whois (samples/clustering/). python-search excluded: single
paragraph block makes reorder infeasible. DRAFT ONLY: nothing sealed, no samples/
writes, no freeze, no judge calls. Template families ARE exposed (sphinx via
appetite/interpreter; iana via example_domains) -> same-family transfer test,
weaker independence than v3; disclosed prominently. Requires user approval
(docs/P_F_V14_PLAN.md section 4) before any formal build/kit/annotation.
Reuses build_case/mutate from build_calibration_set (silver, gold=None ->
provisional assistant expectations; human blind gold is authoritative later).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_calibration_set import build_case, sha256_bytes, dump

CLUSTERING = ROOT / 'samples/clustering'
SLATE_VERSION = 'pf-v4-slate-draft-1'

BASES = [
    {'name': 'iana-abuse', 'short': 'ianaabuse', 'lang': 'en', 'split': 'frozen_test_v4_draft',
     'gold': None, 'exposure': 'same-family transfer (iana template judge-exposed via example_domains)',
     'variants': ['clean', 'missing_paragraph', 'noise', 'duplicate', 'reorder', 'instruction_interference']},
    {'name': 'iana-whois', 'short': 'ianawhois', 'lang': 'en', 'split': 'frozen_test_v4_draft',
     'gold': None, 'exposure': 'same-family transfer (iana template judge-exposed via example_domains)',
     'variants': ['clean', 'missing_paragraph', 'noise', 'duplicate', 'reorder', 'instruction_interference']},
]
# python-search excluded: extract_html yields a single paragraph block ->
# reorder infeasible (no consecutive paragraph pair) and missing_paragraph
# would empty the candidate (different mutation semantics). Documented honest
# feasibility constraint, not score-chasing.



def build_slate():
    cases = []
    for base in BASES:
        for variant in base['variants']:
            try:
                built = build_case(base, variant, CLUSTERING)
            except ValueError as e:
                raise ValueError('Infeasible variant %s on %s: %s' % (variant, base['name'], e))
            built['exposure'] = base['exposure']
            built['source_bytes'] = (CLUSTERING / (base['name'] + '.html')).stat().st_size
            cases.append(built)
    return cases


def render(cases):
    lines = ['# P-F v4 候选 slate 草案（选项 B · 零采集 · 未密封）', '',
             '> **DRAFT / 未批准**：仅为提案。未写 samples/、未冻结、未密封、零 judge 调用。',
             '> 正式构建/盲评 kit/标注须在用户批准 slate 与预算后进行（docs/P_F_V14_PLAN.md）。', '',
             '**独立性披露**：两页从未被 judge 评分，但同属 iana 模板族（经 example_domains 已曝光）',
             '→ 同族同站转移测试，独立性显著弱于 v3 的新模板设计。',
             '选项 A（新采集 2 个新模板短页）仍是推荐路线。', '',
             '| 案例 | 模板 | 变异 | 源字节 | 截断 | prompt_chars |',
             '| --- | --- | --- | ---: | --- | ---: |']
    for c in cases:
        lab = c['label']
        lines.append('| %s | %s | %s | %d | %s | %d |' % (
            c['case_id'], c['manifest_case']['template'], lab['mutation']['type'],
            c['source_bytes'], lab['source_truncated'], c['prompt_chars']))
    counts = {}
    for c in cases:
        t = c['label']['mutation']['type']
        counts[t] = counts.get(t, 0) + 1
    lines += ['', '变异覆盖：' + json.dumps(counts, ensure_ascii=False), '',
              '全部源 ≤20000 字符（BATCH_MAX_SOURCE_CHARS），无截断 → pass 可达。',
              'silver 参考为 extract_html 程序输出（gold=None，provisional）；人类盲评 gold 才是权威。', '']
    return '\n'.join(lines) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description='P-F v4 slate DRAFT (option B, zero calls).')
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args(argv)
    cases = build_slate()
    if len(cases) != 12:
        print('Expected 12 draft cases; got %d' % len(cases), file=sys.stderr)
        return 2
    if any(c['label']['source_truncated'] for c in cases):
        print('Truncation detected; pass unreachable; refusing slate.', file=sys.stderr)
        return 2
    payload = {'slate_version': SLATE_VERSION, 'status': 'DRAFT_UNSEALED_PENDING_APPROVAL',
               'option': 'B (zero-collection same-family transfer; BOTH templates iana family; independence weaker than v3)',
               'judge_version_target': '1.4.0', 'n_cases': len(cases),
               'cases': [{'case_id': c['case_id'], 'manifest_case': c['manifest_case'],
                          'candidate': c['candidate'], 'label': c['label'],
                          'exposure': c['exposure'], 'source_bytes': c['source_bytes']} for c in cases]}
    if args.dry_run:
        print(json.dumps({'dry_run': True, 'n_cases': len(cases),
                          'truncated': 0, 'case_ids': [c['case_id'] for c in cases]}, ensure_ascii=False))
        return 0
    out = Path(args.output)
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    out.mkdir(parents=True)
    (out / 'pf_v4_slate.draft.json').write_text(dump(payload), encoding='utf-8', newline='')
    (out / 'PF_V4_SLATE.md').write_text(render(cases), encoding='utf-8', newline='')
    print(json.dumps({'n_cases': len(cases), 'output': str(out),
                      'case_ids': [c['case_id'] for c in cases]}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
