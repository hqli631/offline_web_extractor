# -*- coding: utf-8 -*-
"""P-F stage-1 dev calibration scorer (zero model calls, config-driven).

Scores FRESH v1.4 judge batches on the dev pool (orig12 + P2 dev6) against the
audited re-adjudication gold view (outputs/pf.dev.gold.v2), reusing the frozen
P-B gate scorer's integrity checks and metrics byte-identical. Optionally also
scores the sealed-gold MECHANICAL track (pre-overlay human gold) for dual-track
disclosure; the mechanical track is NOT the gate basis. This is calibration,
not the gate: the v4 one-shot gate runs later via tools/score_p3_gate.py with
the same frozen config (v3 slot holds v4). Fail-closed on protocol/data-freeze
drift; refuses output overwrite. Anchoring circularity (overlay + re-adjudicated
cases) is disclosed from gold-view provenance, never hidden.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tools.score_p3_gate as g
from tools.ingest_human_labels import aggregate_human
from tools.bootstrap_stats import m_reject, m_false_alarm
from tools.score_judge_results import sha256_bytes

TOOL_VERSION = '1.0.0'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--gate-config', type=Path, required=True)
    ap.add_argument('--dev-batch', action='append', required=True)
    ap.add_argument('--dev-gold', action='append', required=True)
    ap.add_argument('--dev-freeze', action='append', required=True)
    ap.add_argument('--dev-manifest', action='append', default=None)
    ap.add_argument('--dev-silver-dir', action='append', default=None)
    ap.add_argument('--mechanical-gold', action='append', default=None,
                    help='label=path sealed pre-overlay human gold (disclosure track)')
    ap.add_argument('--overlay', type=Path,
                    default=ROOT / 'outputs/pb.gate.inputs.v1/pb.gold.overlay.v1.json',
                    help='P-B adjudicated overlay (code -> case_id mapping for circularity disclosure)')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args(argv)
    out = Path(args.output)
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    cfg = g.load_json(args.gate_config)
    problems = g.validate_gate_config(cfg)
    if problems:
        for p in problems:
            print('GATE-CONFIG: ' + p, file=sys.stderr)
        return 1
    try:
        batches = g._label_path(args.dev_batch, '--dev-batch')
        golds = g._label_path(args.dev_gold, '--dev-gold')
        freezes = g._label_path(args.dev_freeze, '--dev-freeze')
        manifests = g._label_path(args.dev_manifest, '--dev-manifest')
        silvers = g._label_path(args.dev_silver_dir, '--dev-silver-dir')
        mech = g._label_path(args.mechanical_gold, '--mechanical-gold')
    except ValueError as e:
        print('ARGS: ' + str(e), file=sys.stderr)
        return 1
    if not (set(batches) == set(golds) == set(freezes)):
        print('ARGS: dev batch/gold/freeze labels must match', file=sys.stderr)
        return 1
    if mech and set(mech) != set(batches):
        print('ARGS: mechanical-gold labels must match dev batch labels', file=sys.stderr)
        return 1
    if cfg['dev']['match_kappa_subset_label'] not in batches:
        print('GATE-CONFIG: kappa subset label not among dev batches', file=sys.stderr)
        return 1
    integrity, recs, seen = [], {}, set()
    for label, bp in batches.items():
        batch = g.load_json(bp)
        integrity += ['%s: %s' % (label, p) for p in g.check_protocol(batch, cfg)]
        integrity += ['%s: %s' % (label, p) for p in
                      g.check_data_freeze(batch, g.load_json(freezes[label]), manifests.get(label))]
        for row in batch.get('cases', []):
            if row.get('split') != 'development':
                integrity.append('%s: case %s split != development' % (label, row['case_id']))
            if row['case_id'] in seen:
                integrity.append('%s: duplicate dev case %s' % (label, row['case_id']))
            seen.add(row['case_id'])
        try:
            recs[label] = g.records_for(batch, g.load_json(golds[label]),
                                        silvers.get(label, ROOT / 'samples/calibration/labels'))
        except ValueError as e:
            integrity.append('%s: %s' % (label, e))
    if integrity:
        for p in integrity:
            print('INTEGRITY: ' + p, file=sys.stderr)
        return 1
    B, seed = cfg['B'], cfg['seed']
    pooled = [r for rs in recs.values() for r in rs]
    subset_label = cfg['dev']['match_kappa_subset_label']

    def block(rs):
        return {'aggregate': aggregate_human(rs), 'ci95': g.gate_ci_block(rs, B, seed),
                'reject_rate': m_reject(rs), 'false_alarm_rate': m_false_alarm(rs),
                'severe_miss_count': g.severe_miss_count(rs),
                'divergent': [{'case_id': r['case_id'], 'judge': r.get('judge_decision'),
                               'human': r.get('human_decision'), 'false_alarm': bool(r.get('false_alarm')),
                               'severe_miss': bool(r.get('severe_miss'))}
                              for r in rs if r.get('false_alarm') or r.get('severe_miss')
                              or r.get('judge_decision') != r.get('human_decision')]}

    mech_block = None
    if mech:
        mrecs = {}
        for label, bp in batches.items():
            mrecs[label] = g.records_for(g.load_json(bp), g.load_json(mech[label]),
                                         silvers.get(label, ROOT / 'samples/calibration/labels'))
        mp = [r for rs in mrecs.values() for r in rs]
        mech_block = {'by_label': {l: block(rs) for l, rs in mrecs.items()}, 'pooled': block(mp),
                      'note': 'Sealed pre-overlay human gold, mechanical disclosure only; NOT the gate basis.'}
    circular = {'overlay_corrections': [], 'readjudicated_case_ids': [], 'note': ''}
    omap = {c['code']: c['case_id'] for c in g.load_json(args.overlay).get('corrections', [])}
    for label, gp in golds.items():
        gd = g.load_json(gp)
        prov = gd.get('provenance', {})
        codes = prov.get('corrections') or []
        circular['overlay_corrections'] += [{'code': c, 'case_id': omap.get(c)} for c in codes]
        circular['readjudicated_case_ids'] += (prov.get('pf_override') or {}).get('applied_case_ids', [])
    n_circ = len({c['case_id'] for c in circular['overlay_corrections'] if c['case_id']}
                 | set(circular['readjudicated_case_ids']))
    circular['note'] = 'Anchoring circularity on dev track: %d/%d cases (overlay + re-adjudicated); v4 is the independent test.' % (n_circ, len(pooled))
    result = {'tool_version': TOOL_VERSION, 'stage': 'P-F stage-1 dev calibration (NOT the gate)',
              'gate_config_sha256': sha256_bytes(args.gate_config.read_bytes()),
              'judge_version_expected': cfg['batch_config']['judge_version'],
              'seed': seed, 'B': B,
              'inputs': {'dev_batches': {l: sha256_bytes(p.read_bytes()) for l, p in batches.items()},
                         'dev_golds': {l: sha256_bytes(p.read_bytes()) for l, p in golds.items()},
                         'dev_freezes': {l: sha256_bytes(p.read_bytes()) for l, p in freezes.items()}},
              'dev_by_label': {l: block(rs) for l, rs in recs.items()},
              'dev_pooled': block(pooled),
              'kappa_subset': {'label': subset_label,
                               'human_classes': sorted({r.get('human_decision') for r in recs[subset_label]
                                                        if r['judge_status'] == 'accepted'} - {None})},
              'mechanical_track': mech_block, 'circularity': circular,
              'records': {l: rs for l, rs in recs.items()},
              'limitations': ['单一标注者，IAA 未测；一致率不是准确率。',
                              'dev 轨道存在锚定循环（overlay + 重裁决）；独立泛化结论只能来自 v4 一次性测试。',
                              '本输出为阶段1校准，不是 gate；gate 由 score_p3_gate.py 在 v4 密封 gold 后运行。']}
    out.mkdir(parents=True)
    g.write_json(out / 'pf.dev.json', result)
    pa = result['dev_pooled']['aggregate']
    lines = ['# P-F 阶段1 dev 校准摘要（v1.4，非 gate）', '',
             '- judge 期望版本：%s；n=%d；reject=%s severe_miss=%s false_alarm=%s' % (
                 cfg['batch_config']['judge_version'], len(pooled),
                 m_reject(pooled), result['dev_pooled']['severe_miss_count'], m_false_alarm(pooled)),
             '- %s' % circular['note'], '',
             '| 标签 | n | decision_match | kappa |', '| --- | --- | --- | --- |']
    for l, rs in recs.items():
        a = result['dev_by_label'][l]['aggregate']
        lines.append('| %s | %d | %s | %s |' % (l, len(rs), a.get('decision_match_rate'), a.get('decision_cohen_kappa')))
    lines += ['', '双轨：mechanical_track 为密封原始 gold 的机械披露轨，非 gate 依据。',
              '局限：单标注者；一致率≠准确率；dev 锚定循环已披露；v4 才是独立测试。']
    (out / 'PF_DEV_SUMMARY.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='')
    print(json.dumps({'output': str(out), 'n': len(pooled),
                      'pooled': {'reject_rate': m_reject(pooled), 'false_alarm_rate': m_false_alarm(pooled),
                                 'decision_match_rate': pa.get('decision_match_rate')},
                      'severe_miss': result['dev_pooled']['severe_miss_count'],
                      'circularity': circular['note']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
