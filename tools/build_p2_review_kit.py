"""P2 blind review kit builder (zero model calls).

Builds a blind labeling kit for the 18 P2 expansion cases WITHOUT running the
judge: constructs each packet's source/candidate/gold via build_prompt (offline),
reusing render_blind_packet/build_template/ordered_cases from build_human_review_kit.
Packets contain no judge/silver/program scores and no real case ids (neutral P##
codes + sealed mapping). Enables independent human gold labeling (WP4) and second
annotator IAA. Refuses overwrite of existing output dir.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.build_human_review_kit import (render_blind_packet, build_template,
                                          ordered_cases, write_text)
from tools.build_calibration_set import ROOT, sha256_bytes
from src.webextractor.rubrics_judge import build_prompt

KIT_VERSION = 'p2-1.0.0'


def _case_row(mc, samples_root):
    sb = (samples_root / mc['source']).read_bytes()
    cand = json.loads((samples_root / mc['candidate']).read_text(encoding='utf-8-sig'))
    predicted = {'title': cand['title'], 'blocks': cand['blocks']}
    gold = None
    if mc.get('gold'):
        g = json.loads((samples_root / mc['gold']).read_text(encoding='utf-8-sig'))
        gold = {'title': g['title'], 'blocks': g['blocks']}
    prompt, _reg, meta = build_prompt(sb, predicted, gold, max_source_chars=20000)
    mode = 'with_gold' if gold is not None else 'source_only'
    return {'case_id': mc['case_id'], 'split': mc['split'], 'template': mc['template'],
            'case_meta': {'mode': mode, 'source_truncated': meta['source_truncated']},
            'report': {'prompt': prompt, 'mode': mode}}


def main(argv=None):
    ap = argparse.ArgumentParser(description='Build P2 blind review kit (no judge calls).')
    ap.add_argument('--manifest', type=Path, default=ROOT / 'samples/p2_manifest.json')
    ap.add_argument('--freeze', type=Path, default=ROOT / 'outputs/p2.freeze.v5.json')
    ap.add_argument('--output', type=Path, default=ROOT / 'outputs/human_review/p2.blind.v1')
    args = ap.parse_args(argv)
    out = Path(args.output)
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    samples_root = ROOT / 'samples'
    rows = [_case_row(mc, samples_root) for mc in manifest['cases']]
    fake_batch = {'cases': rows}
    rows = ordered_cases(fake_batch)
    codes = {r['case_id']: 'P%02d' % i for i, r in enumerate(rows, 1)}
    out.mkdir(parents=True)
    (out / 'packets').mkdir()
    rels = []
    for i, row in enumerate(rows, 1):
        code = codes[row['case_id']]
        rel = 'packets/%s.md' % code
        write_text(out / rel, render_blind_packet(row, i, len(rows), code))
        rels.append(rel)
    template = build_template(fake_batch, codes)
    template['instructions'] = ('P2 扩样盲评：逐案填写 decision(pass/uncertain/fail) 与五维 score(0-4/null)/status/severity；'
                                'source_only 例 decision 只能 uncertain/fail。先填 annotator 与 annotation_date。'
                                '独立判断，勿查阅 judge/silver/程序分数或其他案卷，避免锚定。')
    for rel, text in (
            ('human_labels.blind.json', json.dumps(template, ensure_ascii=False, indent=2) + '\n'),
            ('sealed_mapping.json', json.dumps({codes[r['case_id']]: r['case_id'] for r in rows}, ensure_ascii=False, indent=2) + '\n')):
        write_text(out / rel, text)
        rels.append(rel)
    dev = [codes[r['case_id']] for r in rows if r['split'] == 'development']
    test = [codes[r['case_id']] for r in rows if r['split'] == 'frozen_test']
    index = ['# P2 扩样 · 盲评索引', '',
             '共 %d 例（dev 扩展 %d / frozen_test v2 %d）。中性编号 P01–P%02d，密封映射见 sealed_mapping.json（标注完成前勿查阅）。' % (len(rows), len(dev), len(test), len(rows)), '',
             '## 工作流',
             '1. 按顺序读 packets/P##.md（候选+参考答案+源证据+评分速查，不含 judge/silver 分数）。',
             '2. 在 human_labels.blind.json 对应 blind_code 条目填 decision 与五维。',
             '3. 先填 annotator 与 annotation_date。',
             '4. 填完发回助手做校验与接收。', '',
             '## IAA（第二标注者）',
             '第二标注者独立复核至少 12 例（dev/test 混合），用相同案卷、独立填写另一份标签文件；助手用 compute_iaa.py 计算标注者间 kappa。', '',
             'dev: ' + ', '.join(dev), 'frozen_test v2: ' + ', '.join(test)]
    write_text(out / 'INDEX.md', '\n'.join(index) + '\n')
    rels.append('INDEX.md')
    kit_manifest = {'kit_version': KIT_VERSION,
                    'inputs': {'manifest': sha256_bytes(args.manifest.read_bytes()),
                               'freeze': sha256_bytes(args.freeze.read_bytes())},
                    'n_cases': len(rows),
                    'files': {rel: sha256_bytes((out / rel).read_bytes()) for rel in sorted(rels)}}
    write_text(out / 'kit_manifest.json', json.dumps(kit_manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output': str(out), 'n_cases': len(rows), 'development': len(dev),
                      'frozen_test': len(test)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
