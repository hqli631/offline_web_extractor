# -*- coding: utf-8 -*-
"""P3 calibration review kit builder (zero model calls, unblinded post-hoc).

Derives divergence cases from the SEALED P2 judge batch + human gold using
explicit criteria, renders evidence-comparison packets (candidate/source/gold
evidence + judge citations + human labels + silver mutation metadata), and a
findings template for the reviewer. Discipline: P2 gold is NOT rewritten;
frozen_test v2 is NOT re-scored; any protocol/anchor revision must go through
a pre-registered freeze amendment (judge v1.3 candidate). Refuses overwrite.

Selection criteria (documented, deterministic):
  decision_mismatch | dim_gap_ge2 (|judge-human|>=2 on comparable dims)
  | judge_missed_defect (human minor/major/critical, judge none)
  | judge_severe_human_not (judge major/critical, human not severe)
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.score_p2_results import check_p2_freeze, load_json, write_json
from tools.score_judge_results import sha256_bytes

TOOL_VERSION = '1.0.0'
DIMS = ('completeness', 'cleanliness', 'structure', 'title', 'format')
SEVERE = ('major', 'critical')
DEFECT = ('minor', 'major', 'critical')
VERDICTS = ('judge_correct', 'human_correct', 'anchor_ambiguous', 'both_partially_correct')


def write_text(p, t):
    Path(p).write_text(t, encoding='utf-8', newline='')


def select_divergences(cases, gold_map):
    out = []
    for row in cases:
        rep = row.get('report') or {}
        if rep.get('status') != 'accepted':
            out.append({'case_id': row['case_id'], 'split': row['split'],
                        'categories': ['judge_rejected'], 'judge_decision': None,
                        'human_decision': (gold_map.get(row['case_id']) or {}).get('decision')})
            continue
        a = rep['assessment']
        h = gold_map.get(row['case_id'])
        if h is None:
            continue
        cats = []
        if a['decision'] != h['decision']:
            cats.append('decision_mismatch')
        for n in DIMS:
            jd, hd = a['dimensions'][n], h['dimensions'][n]
            js, hs = jd.get('score'), hd.get('score')
            if type(js) is int and type(hs) is int and abs(js - hs) >= 2:
                cats.append('dim_gap_ge2:' + n)
            if hd.get('severity') in DEFECT and jd.get('severity') == 'none':
                cats.append('judge_missed_defect:' + n)
            if jd.get('severity') in SEVERE and hd.get('severity') not in SEVERE:
                cats.append('judge_severe_human_not:' + n)
        if cats:
            out.append({'case_id': row['case_id'], 'split': row['split'],
                        'categories': sorted(set(cats)), 'judge_decision': a['decision'],
                        'human_decision': h['decision']})
    return out


def resolve_ref(prompt, ref):
    if ref == 's:html':
        return '[raw HTML prefix, %d chars]' % len(prompt['source'].get('html', ''))
    if ref in ('p:title', 'g:title'):
        doc = prompt['candidate'] if ref.startswith('p') else prompt.get('gold') or {}
        return doc.get('title') or ''
    kind, _, idx = ref.partition(':')
    try:
        i = int(idx)
    except ValueError:
        return ''
    if kind == 's':
        nodes = prompt['source'].get('nodes', [])
        return nodes[i]['text'] if i < len(nodes) else ''
    doc = prompt['candidate'] if kind == 'p' else prompt.get('gold') or {}
    blocks = doc.get('blocks', [])
    return blocks[i].get('text', '') if i < len(blocks) else ''


def trunc(t, n=220):
    t = t or ''
    return t if len(t) <= n else t[:n] + '…[截断显示]'


def mutation_evidence(mut, prompt):
    lines = []
    mt = (mut or {}).get('type')
    cand = prompt['candidate'].get('blocks', [])
    gold = (prompt.get('gold') or {}).get('blocks', [])
    if mt in ('instruction_interference', 'noise'):
        txt = mut.get('injected_text', '')
        lines.append('**注入/噪声文本（verbatim）**：')
        lines.append('> ' + txt.replace('\n', '\n> '))
        hits = [i for i, b in enumerate(cand) if txt and txt[:60] in b.get('text', '')]
        if hits:
            for i in hits:
                lines.append('')
                lines.append('候选 p:%d（kind=%s）**包含上述文本**：' % (i, cand[i].get('kind')))
                lines.append('> ' + cand[i].get('text', '').replace('\n', '\n> '))
        else:
            lines.append('')
            lines.append('候选中未找到包含该文本的块（提取器可能已排除）。')
    elif mt == 'missing_paragraph':
        ex = mut.get('removed_excerpt', '')
        lines.append('**被移除段落摘录（verbatim）**：')
        lines.append('> ' + ex)
        for i, b in enumerate(gold):
            if ex and ex[:60] in b.get('text', ''):
                lines.append('')
                lines.append('参考 g:%d 含该段落（候选应缺失）：' % i)
                lines.append('> ' + trunc(b.get('text', ''), 400))
    elif mt == 'duplicate':
        ex = mut.get('duplicated_excerpt', '')
        lines.append('**被重复段落摘录（verbatim）**：')
        lines.append('> ' + ex)
        hits = [i for i, b in enumerate(cand) if ex and ex[:60] in b.get('text', '')]
        lines.append('')
        lines.append('候选中出现 %d 次：%s' % (len(hits), ', '.join('p:%d' % i for i in hits) or '无'))
    elif mt == 'reorder':
        idxs = mut.get('indices', [])
        lines.append('**乱序涉及参考块 indices=%s**：' % idxs)
        for i in idxs:
            if i < len(gold):
                lines.append('- g:%d: %s' % (i, trunc(gold[i].get('text', ''), 160)))
        lines.append('')
        lines.append('候选对应位置（前 %d 块）：' % (max(idxs) + 2 if idxs else 4))
        for i, b in enumerate(cand[:max(idxs) + 2 if idxs else 4]):
            lines.append('- p:%d (%s): %s' % (i, b.get('kind'), trunc(b.get('text', ''), 120)))
    else:
        lines.append('无受控变异（clean）：分歧源于对自然源内容的判断差异。')
    return lines


def render_packet(sel, row, gold_entry, mut, code):
    rep = row['report']
    a = rep.get('assessment') or {}
    prompt = rep.get('prompt') or {}
    L = ['# P3 校准复审案卷 %s · %s' % (code, sel['case_id']), '',
         '- split：%s ｜ template：%s ｜ 变异：%s' % (sel['split'], row.get('template'), (mut or {}).get('type')),
         '- 分歧类别：%s' % ', '.join(sel['categories']),
         '- 决策：judge=%s ｜ human=%s' % (sel['judge_decision'], sel['human_decision']), '',
         '## 1. 维度对照（human vs judge）', '',
         '| 维度 | human score/status/severity | judge score/status/severity | judge reason |',
         '| --- | --- | --- | --- |']
    for n in DIMS:
        hd = gold_entry['dimensions'][n]
        jd = (a.get('dimensions') or {}).get(n) or {}
        L.append('| %s | %s/%s/%s | %s/%s/%s | %s |' % (
            n, hd.get('score'), hd.get('status'), hd.get('severity'),
            jd.get('score'), jd.get('status'), jd.get('severity'),
            trunc((jd.get('reason') or '').replace('|', '/').replace('\n', ' '), 260)))
    L += ['', 'human overall_note：%s' % gold_entry.get('overall_note', '')]
    if 'injection_complied' in gold_entry:
        L.append('human injection_complied：%s' % gold_entry['injection_complied'])
    L += ['', '## 2. judge 引用证据（ref → 原文）']
    for n in DIMS:
        jd = (a.get('dimensions') or {}).get(n) or {}
        ev = jd.get('evidence') or []
        if jd.get('severity') == 'none' and jd.get('score') == 4:
            continue
        if not ev:
            continue
        L.append('')
        L.append('### %s' % n)
        for e in ev:
            L.append('- %s 引用「%s」 → 原文：%s' % (e.get('ref'), e.get('quote'), trunc(resolve_ref(prompt, e.get('ref', '')), 200)))
    L += ['', '## 3. 变异证据（silver 元数据 + 候选/参考定位）', '']
    L += mutation_evidence(mut, prompt)
    L += ['', '## 4. 复审问题', '',
          '1. judge 的严重度判定是否有候选/源证据支持？（对照 §2/§3）',
          '2. human 标签是否漏检或过严？',
          '3. 若双方都有道理：锚点表述（4=无明显缺陷 / 3=小局部缺陷 / 2=明显中度损失或污染 / major=明显中度损失/污染/乱序/属性错误）是否存在歧义？需要怎样的澄清？', '',
          '在 p3_findings.json 对应条目填写：verdict ∈ %s；anchor_revision_suggestion（可选）；note（简短中文）。' % (VERDICTS,), '',
          '**纪律**：本复审不回改 P2 封存 gold、不重评 frozen_test v2；结论仅用于校准 findings 与预注册修订提案。']
    return '\n'.join(L) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description='Build P3 calibration review kit (offline, unblinded).')
    ap.add_argument('--p2-batch', type=Path, default=ROOT / 'outputs/p2.judge.v2.json')
    ap.add_argument('--gold', type=Path, default=ROOT / 'outputs/human_review/p2.gold.v1/human_gold.p2.blind.json')
    ap.add_argument('--manifest', type=Path, default=ROOT / 'samples/p2_manifest.json')
    ap.add_argument('--freeze', type=Path, default=ROOT / 'outputs/p2.freeze.v5.json')
    ap.add_argument('--output', type=Path, default=ROOT / 'outputs/human_review/p3.calibration.v1')
    args = ap.parse_args(argv)
    out = Path(args.output)
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    batch = load_json(args.p2_batch)
    freeze = load_json(args.freeze)
    problems = check_p2_freeze(batch, freeze, args.manifest)
    gold = load_json(args.gold)
    prov = gold.get('provenance') or {}
    if prov.get('freeze_sha256') != sha256_bytes(args.freeze.read_bytes()):
        problems.append('gold provenance freeze sha mismatch')
    if prov.get('manifest_sha256') != freeze.get('manifest_sha256'):
        problems.append('gold provenance manifest sha mismatch')
    labels_rel = ROOT / 'outputs/human_review/p2.blind.v1/human_labels.blind.r2.json'
    if labels_rel.exists() and prov.get('labels_sha256') != sha256_bytes(labels_rel.read_bytes()):
        problems.append('gold provenance labels sha mismatch (r2 changed after sealing)')
    if problems:
        for p in problems:
            print('INTEGRITY: ' + p, file=sys.stderr)
        return 1
    gm = {c['case_id']: c for c in gold['cases']}
    by_id = {r['case_id']: r for r in batch['cases']}
    sel = select_divergences(batch['cases'], gm)
    out.mkdir(parents=True)
    (out / 'packets').mkdir()
    rels = []
    findings_cases = []
    for i, s in enumerate(sel, 1):
        code = 'C%02d' % i
        cid = s['case_id']
        row = by_id[cid]
        mut = None
        lp = ROOT / 'samples/calibration/labels' / (cid + '.label.json')
        if lp.exists():
            mut = (load_json(lp).get('mutation') or {})
        rel = 'packets/%s.md' % code
        write_text(out / rel, render_packet(s, row, gm[cid], mut, code))
        rels.append(rel)
        findings_cases.append({'code': code, 'case_id': cid, 'split': s['split'],
                               'categories': s['categories'], 'verdict': None,
                               'anchor_revision_suggestion': '', 'note': ''})
    template = {'findings_version': 1, 'reviewer': '', 'review_date': '',
                'discipline_ack': False,
                'discipline': '不回改 P2 封存 gold；不重评 frozen_test v2；修订须预注册。',
                'verdicts': list(VERDICTS), 'cases': findings_cases}
    write_json(out / 'p3_findings.json', template)
    rels.append('p3_findings.json')
    idx = ['# P3 校准复审索引', '',
           '分歧案卷 %d 例（判据：decision_mismatch / dim_gap_ge2 / judge_missed_defect / judge_severe_human_not）。' % len(sel),
           '解封呈现（事后复审，非盲评）：真实案例名 + judge 证据 + human gold + silver 变异。', '',
           '## 类别', '- A 注入漏检：instruction_interference 3 例（候选含注入块，human 给 4/none）',
           '- B judge 偏严：noise/missing 4 例（judge major vs human minor）',
           '- C judge 漏标：human minor 而 judge none（nasa-clean/nasa-duplicate/w3ca11y-reorder）', '',
           '## 工作流', '1. 逐案读 packets/C##.md（§1 对照 → §2 judge 引用 → §3 变异证据）。',
           '2. 在 p3_findings.json 填 reviewer/review_date/discipline_ack=true 与逐案 verdict/note。',
           '3. 交回助手汇总 findings；如需锚点修订 → 预注册 freeze 修订提案（judge v1.3 候选），不事后调参。', '',
           '## 案卷清单']
    for fc in findings_cases:
        idx.append('- %s %s [%s]：%s' % (fc['code'], fc['case_id'], fc['split'], ', '.join(fc['categories'])))
    write_text(out / 'INDEX.md', '\n'.join(idx) + '\n')
    rels.append('INDEX.md')
    km = {'kit_version': 'p3-' + TOOL_VERSION,
          'inputs': {'p2_batch': sha256_bytes(args.p2_batch.read_bytes()),
                     'gold': sha256_bytes(args.gold.read_bytes()),
                     'freeze': sha256_bytes(args.freeze.read_bytes()),
                     'manifest': sha256_bytes(args.manifest.read_bytes())},
          'n_cases': len(sel), 'criteria': 'decision_mismatch|dim_gap_ge2|judge_missed_defect|judge_severe_human_not',
          'files': {rel: sha256_bytes((out / rel).read_bytes()) for rel in sorted(rels)}}
    write_json(out / 'kit_manifest.json', km)
    rels.append('kit_manifest.json')
    print(json.dumps({'output': str(out), 'n_cases': len(sel),
                      'cases': [f['case_id'] for f in findings_cases]}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
