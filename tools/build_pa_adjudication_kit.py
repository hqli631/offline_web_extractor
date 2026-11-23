# -*- coding: utf-8 -*-
"""P-A adjudication kit builder (zero model calls, unblinded post-hoc).

Targets the OPEN judge-human-program divergences NOT covered by the sealed
P0 (23 cases) / P3 (C01-C10) adjudications:
  A01 cal-appetite-reorder  : v1.2 false alarm (judge structure major vs human minor)
  A02 n5-blurb-title        : judge minor (double-space collapse) vs program/human title=4
  A03 cal-appetite-noise    : v1.3 severe_miss (human cleanliness major vs v1.3 minor)
  A04 cal-blurb-noise       : v1.3 severe_miss (human cleanliness major vs v1.3 minor)
  A05 cal-blurb-reorder     : v1.3 severe_miss (human structure critical vs v1.3 minor)
A03-A05 expose the gold generational calibration conflict behind the P3 gate FAIL.
Discipline: sealed gold (P0 final.v1 / P2 gold.v1) is NEVER rewritten; this kit only
produces a findings template. Any protocol amendment requires P-B pre-registration.
Refuses overwrite (exit 3).
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.webextractor.extractor import extract_html
from src.webextractor.rubrics_v2 import score as program_score
from tools.build_p3_review_kit import resolve_ref, trunc, mutation_evidence

VERDICTS = ('judge_correct', 'human_correct', 'anchor_ambiguous', 'both_partially_correct')
KIT_VERSION = 'pa-1'


def load_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def write_json(p, v):
    Path(p).write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='')


def write_text(p, t):
    Path(p).write_text(t, encoding='utf-8', newline='')


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def render_judge(label, rep):
    a = rep.get('assessment') or {}
    L = ['**%s**（judge v%s · mode=%s · status=%s）' % (label, rep.get('judge_version'), rep.get('mode'), rep.get('status')),
         '- decision：**%s**' % a.get('decision')]
    for k, v in (a.get('dimensions') or {}).items():
        L.append('- %s：score=%s severity=%s status=%s' % (k, v.get('score'), v.get('severity'), v.get('status')))
        if v.get('reason'):
            L.append('  - reason：%s' % v['reason'])
        for e in (v.get('evidence') or []):
            resolved = resolve_ref(rep.get('prompt') or {}, e.get('ref', ''))
            L.append('  - evidence %s：「%s」 → 解析：「%s」' % (e.get('ref'), trunc(e.get('quote', ''), 160), trunc(resolved, 160)))
    return L


def render_gold(g):
    L = ['**人类 gold（封存 · 不可回改）**', '- decision：**%s**' % g.get('decision')]
    for k, v in (g.get('dimensions') or {}).items():
        note = (' note=' + v['note']) if v.get('note') else ''
        L.append('- %s：score=%s severity=%s%s' % (k, v.get('score'), v.get('severity'), note))
    if g.get('overall_note'):
        L.append('- overall_note：%s' % g['overall_note'])
    if g.get('adjudication_note'):
        L.append('- adjudication_note：%s' % g['adjudication_note'])
    return L


def mutation_meta(cid):
    lp = ROOT / 'samples/calibration/labels' / (cid + '.label.json')
    if lp.exists():
        return load_json(lp).get('mutation') or {}
    return {}


def cal_packet(code, cid, question, v12, v13, gold, mut):
    L = ['# P-A 裁决案卷 %s · %s' % (code, cid), '',
         '- 分歧类型：%s' % ('v1.2 误报（judge 偏严）' if v13 is None else 'v1.3 severe_miss（gold 代际校准冲突）'),
         '- 裁决问题：**%s**' % question, '',
         '## 1. 受控变异证据（verbatim）']
    prompt = (v13 or v12).get('prompt') or {}
    L += mutation_evidence(mut, prompt)
    L += ['', '## 2. Judge 评估']
    if v12:
        L += render_judge('judge v1.2（冻结协议）', v12) + ['']
    if v13:
        L += render_judge('judge v1.3（已回滚修订）', v13) + ['']
    L += ['## 3. 人类 gold'] + render_gold(gold)
    L += ['', '## 4. 裁决',
          '在 pa_findings.json 对应条目填写：verdict ∈ %s；anchor_revision_suggestion（可选，供 P-B 预注册修订参考）；note（简短中文）。' % (VERDICTS,),
          '提示：本案旨在裁定严重度锚点（major/minor/critical 的边界），而非简单判谁对。若认为锚点本身需按缺陷量级细化，请填 anchor_ambiguous 并给出建议。', '',
          '纪律：不回改封存 gold；不重评 frozen_test；修订须 P-B 预注册。']
    return '\n'.join(L) + '\n'


def blurb_title_packet(code, cid, question, critic, gold_clean, expected_path, source_path):
    sb = Path(source_path).read_bytes()
    base = extract_html(sb)
    baseline = {'title': base.title, 'blocks': base.to_dict()['blocks']}
    gold = load_json(expected_path)
    ps = program_score(baseline, gold)
    import re
    raw_title = ''
    m = re.search(rb'<title[^>]*>(.*?)</title>', sb, re.S | re.I)
    if m:
        raw_title = m.group(1).decode('utf-8', errors='replace')
    L = ['# P-A 裁决案卷 %s · %s' % (code, cid), '',
         '- 分歧类型：judge vs 程序侧核 vs 人类 gold（标题空白归一化）',
         '- 裁决问题：**%s**' % question, '',
         '## 1. 源标题（verbatim）',
         '- 源 <title> 原始内容：「%s」' % raw_title.strip(),
         '- 候选标题（extract_html 归一化后）：「%s」' % baseline.get('title', ''),
         '- 参考 expected.json 标题：「%s」' % gold.get('title', ''),
         '- 注：源标题含连续双空格；extract_html 与 rubrics_v2 均按 whitespace 归一化（split+join）→ 精确匹配。', '',
         '## 2. Judge 评估（Node 5 Critic，source_only）']
    L += render_judge('judge v1.2', critic)
    L += ['', '## 3. 程序化侧核（rubrics_v2 vs expected，post-hoc）',
          '- title：score=%s exact=%s（归一化后精确匹配）' % (ps['dimensions']['title'].get('score'), ps['dimensions']['title'].get('exact')),
          '- decision：%s ｜ recall=%s precision=%s' % (ps['decision'], ps['dimensions']['completeness'].get('recall'), ps['dimensions']['cleanliness'].get('precision')),
          '- 程序侧不评估空白保真：双空格折叠被视为归一化而非缺陷。', '',
          '## 3b. 人类 gold（cal-blurb-clean，封存）']
    L += render_gold(gold_clean)
    L += ['', '## 4. 裁决',
          '在 pa_findings.json 填写 verdict ∈ %s；anchor_revision_suggestion（标题空白保真政策）；note。' % (VERDICTS,),
          '提示：judge_correct=双空格折叠应记 minor 缺陷（源保真）；human_correct=空白归一化可接受（程序与人类一致）；anchor_ambiguous=标题锚点需明确空白政策。', '',
          '纪律：不回改封存 gold；修订须 P-B 预注册。']
    return '\n'.join(L) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description='Build P-A adjudication kit (offline, unblinded, zero calls).')
    ap.add_argument('--output', type=Path, default=ROOT / 'outputs/human_review/pa.adjudication.v1')
    args = ap.parse_args(argv)
    out = Path(args.output)
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    v12_batch = load_json(ROOT / 'outputs/p1_5.dev.v1.json')
    v13_batch = load_json(ROOT / 'outputs/p3.dev.orig.v1.json')
    gold = load_json(ROOT / 'outputs/human_review/final.v1/human_gold.final.json')
    n5 = load_json(ROOT / 'outputs/node5.run.v1.json')
    v12 = {r['case_id']: r['report'] for r in v12_batch['cases']}
    v13 = {r['case_id']: r['report'] for r in v13_batch['cases']}
    gm = {c['case_id']: c for c in gold['cases']}
    n5b = next(r for r in n5['cases'] if r['case_id'] == 'n5-blurb')
    out.mkdir(parents=True)
    (out / 'packets').mkdir()
    cases = []
    rels = []

    def emit(code, cid, dtype, question, text):
        rel = 'packets/%s.md' % code
        write_text(out / rel, text)
        rels.append(rel)
        cases.append({'code': code, 'case_id': cid, 'divergence_type': dtype,
                      'adjudication_question': question, 'verdict': None,
                      'anchor_revision_suggestion': '', 'note': ''})

    q1 = '块乱序（reorder）在 structure 维应记 major（judge v1.2）还是 minor（人类 gold）？严重度是否应按乱序量级区分？'
    emit('A01', 'cal-appetite-reorder', 'v12_false_alarm', q1,
         cal_packet('A01', 'cal-appetite-reorder', q1, v12['cal-appetite-reorder'], None,
                    gm['cal-appetite-reorder'], mutation_meta('cal-appetite-reorder')))
    q2 = '标题中连续双空格被折叠为单空格，应记 title minor 缺陷（judge，源保真）还是可接受归一化（程序+人类=4）？'
    emit('A02', 'n5-blurb-title', 'judge_vs_program_title', q2,
         blurb_title_packet('A02', 'n5-blurb-title', q2, n5b['critic'], gm['cal-blurb-clean'],
                            ROOT / 'samples/python_blurb.expected.json', ROOT / 'samples/python_blurb.html'))
    for code, cid in [('A03', 'cal-appetite-noise'), ('A04', 'cal-blurb-noise'), ('A05', 'cal-blurb-reorder')]:
        dim = 'structure' if cid.endswith('reorder') else 'cleanliness'
        gsev = gm[cid]['dimensions'][dim]['severity']
        q = '单个噪声块/相邻段落乱序在 %s 维：人类 gold 记 %s，v1.3 记 minor（severe_miss）。哪个符合缺陷量级？v1.2 曾与人类一致——v1.3 粒度原则是否过宽？' % (dim, gsev)
        emit(code, cid, 'v13_severe_miss_anchor', q,
             cal_packet(code, cid, q, v12.get(cid), v13.get(cid), gm[cid], mutation_meta(cid)))

    template = {'findings_version': 1, 'kit_version': KIT_VERSION, 'reviewer': '', 'review_date': '',
                'discipline_ack': False,
                'discipline': '不回改 P0/P2 封存 gold；不重评 frozen_test v1/v2/v3；裁决仅产生 findings；协议修订须 P-B 预注册；单标注者（IAA 缺失已声明）。',
                'verdicts': list(VERDICTS), 'cases': cases}
    write_json(out / 'pa_findings.json', template)
    rels.append('pa_findings.json')
    sources = {'outputs/p1_5.dev.v1.json': sha256_bytes((ROOT / 'outputs/p1_5.dev.v1.json').read_bytes()),
               'outputs/p3.dev.orig.v1.json': sha256_bytes((ROOT / 'outputs/p3.dev.orig.v1.json').read_bytes()),
               'outputs/human_review/final.v1/human_gold.final.json': sha256_bytes((ROOT / 'outputs/human_review/final.v1/human_gold.final.json').read_bytes()),
               'outputs/node5.run.v1.json': sha256_bytes((ROOT / 'outputs/node5.run.v1.json').read_bytes())}
    manifest = {'kit_version': KIT_VERSION, 'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'source_artifacts_sha256': sources, 'cases': [{'code': c['code'], 'case_id': c['case_id']} for c in cases],
                'discipline': template['discipline']}
    write_json(out / 'kit_manifest.json', manifest)
    rels.append('kit_manifest.json')
    idx = ['# P-A 裁决索引（5 例开放分歧）', '',
           '事后解封裁决（非盲评）：真实案例名 + judge 证据 + 人类 gold + 程序侧核 + 受控变异。', '',
           '## 背景',
           'P3 gate FAIL 的 3 例 v1.2 false_alarm 中，2 例（C01/C02）已由 P3 裁决为 judge_correct（人类 gold 漏检）。',
           '本 kit 覆盖**剩余开放分歧**：A01 是唯一未解释的 v1.2 误报；A02 是 Node 5 新发现的 judge–程序标题分歧；',
           'A03–A05 是 v1.3 severe_miss 护栏 FAIL 的 3 例，暴露 **gold 代际校准冲突**（同型变异人类严重度不一致）。', '',
           '## 案卷',
           '| 代码 | 案例 | 分歧 | 裁决问题 |', '| --- | --- | --- | --- |']
    for c in cases:
        idx.append('| %s | %s | %s | %s |' % (c['code'], c['case_id'], c['divergence_type'], c['adjudication_question']))
    idx += ['', '## 填写', '在 pa_findings.json 填 reviewer/review_date/discipline_ack=true，逐案 verdict + anchor_revision_suggestion + note。',
            'verdicts：%s' % (VERDICTS,), '',
            '## 纪律', template['discipline'], '',
            '## 复现', 'python -m tools.build_pa_adjudication_kit --output outputs/human_review/pa.adjudication.v1（拒绝覆盖；零调用）']
    write_text(out / 'INDEX.md', '\n'.join(idx) + '\n')
    rels.append('INDEX.md')
    print(json.dumps({'output': str(out), 'cases': len(cases), 'files': rels}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
