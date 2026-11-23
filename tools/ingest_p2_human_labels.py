# -*- coding: utf-8 -*-
"""P2 human-gold ingestion (offline, zero model calls, fail-closed).

Validates the filled P2 blind label file against Rubrics v2 protocol rules
(mirroring judge validate_assessment where applicable), verifies kit/freeze
integrity (zero drift), unblinds via the sealed mapping and snapshots human
gold. No judge comparison happens here: the judge batch runs AFTER gold is
sealed, so gold can never be anchored to judge output.

Validation is stricter than the P0 validator in three documented ways:
  * not_applicable requires severity none (judge protocol constraint);
  * integer score < 4 requires severity minor/major/critical (gold cannot
    carry 'unknown' severity with a numeric score);
  * decision must follow the protocol's deterministic rule (severe -> fail;
    truncated source OR any partial/unscored/non-none severity -> uncertain;
    otherwise pass). Truncation forces uncertain exactly as the judge's
    mechanical scored->partial downgrade does; human status fields are not
    forced to partial (they record annotator confidence; the judge status
    downgrade is a mechanical artifact documented in the report).
Errors are rendered with blind codes only; real case ids never leak through
validation messages. Output dir refuses overwrite (exit 3).
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.score_judge_results import DIMS, SEVERE, sha256_bytes
from tools.build_calibration_set import sha256_json
from src.webextractor.rubrics_judge import build_prompt

TOOL_VERSION = '1.0.0'
DECISIONS = ('pass', 'uncertain', 'fail')
STATUSES = ('scored', 'partial', 'unscored', 'not_applicable')
SEVERITIES = ('none', 'minor', 'major', 'critical', 'unknown')
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
MAX_SOURCE_CHARS = 20000  # frozen batch_config (freeze v4/v5); kit built with the same limit


def write_text(path, text):
    Path(path).write_text(text, encoding='utf-8', newline='')


def write_json(path, value):
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def case_meta(mc, samples_root):
    sb = (samples_root / mc['source']).read_bytes()
    cand = load_json(samples_root / mc['candidate'])
    pred = {'title': cand['title'], 'blocks': cand['blocks']}
    gold = None
    if mc.get('gold'):
        g = load_json(samples_root / mc['gold'])
        gold = {'title': g['title'], 'blocks': g['blocks']}
    _p, _r, meta = build_prompt(sb, pred, gold, max_source_chars=MAX_SOURCE_CHARS)
    return {'mode': 'with_gold' if gold is not None else 'source_only',
            'source_truncated': meta['source_truncated']}


def verify_integrity(manifest_path, freeze_path, kit_dir, manifest, freeze, slate_path=None):
    problems = []
    manifest_file_sha = sha256_bytes(manifest_path.read_bytes())
    manifest_rel = manifest_path.resolve().relative_to(ROOT.resolve()).as_posix()
    recorded_file_sha = (freeze.get('files') or {}).get(manifest_rel)
    if manifest_file_sha != recorded_file_sha:
        problems.append('manifest file sha256 does not match freeze files entry for ' + manifest_rel)
    if sha256_json(manifest) != freeze.get('manifest_sha256'):
        problems.append('manifest canonical JSON sha256 does not match freeze manifest_sha256')
    for rel, recorded in (freeze.get('files') or {}).items():
        p = ROOT / rel
        if not p.exists():
            problems.append('freeze file missing: ' + rel)
        elif sha256_bytes(p.read_bytes()) != recorded:
            problems.append('freeze file drift: ' + rel)
    kit_manifest = load_json(kit_dir / 'kit_manifest.json')
    inputs = kit_manifest.get('inputs') or {}
    freeze_sha = sha256_bytes(freeze_path.read_bytes())
    if slate_path is not None:
        # P-F v4 kit layout: inputs.slate -> formal slate -> manifest/freeze shas.
        slate = load_json(slate_path)
        if inputs.get('slate') != sha256_bytes(slate_path.read_bytes()):
            problems.append('kit slate input sha does not match slate file')
        if slate.get('manifest_sha256') != manifest_file_sha:
            problems.append('slate manifest sha does not match current manifest file')
        if slate.get('freeze_sha256') != freeze_sha:
            problems.append('slate freeze sha does not match freeze file')
    else:
        if inputs.get('manifest') != manifest_file_sha:
            problems.append('kit manifest input sha does not match current manifest file')
        base_sha = (freeze.get('amendment') or {}).get('base_freeze_sha256')
        if inputs.get('freeze') not in (freeze_sha, base_sha):
            problems.append('kit freeze input sha does not match freeze file or its amendment base')
    for rel, recorded in (kit_manifest.get('files') or {}).items():
        if rel == 'human_labels.blind.json':
            continue  # filled by the annotator; expected to differ from template
        p = kit_dir / rel
        if not p.exists() or sha256_bytes(p.read_bytes()) != recorded:
            problems.append('kit file drift: ' + rel)
    return problems, kit_manifest


def validate_labels(doc, mapping, metas, silver_mutations):
    """Return (errors, warnings). Blind codes only in messages."""
    errors, warnings = [], []
    if doc.get('label_version') != 1:
        errors.append('label_version must be 1')
    if doc.get('stage') != 'blind':
        errors.append('stage must be blind')
    annotator = doc.get('annotator')
    if not isinstance(annotator, str) or not annotator.strip():
        errors.append('annotator must be a nonempty string')
    date = doc.get('annotation_date')
    if not isinstance(date, str) or not DATE_RE.match(date):
        errors.append('annotation_date must be YYYY-MM-DD')
    entries = doc.get('cases')
    if not isinstance(entries, list):
        return errors + ['cases must be a list'], warnings
    seen = {}
    for e in entries:
        if not isinstance(e, dict):
            errors.append('case entry must be an object')
            continue
        code = e.get('blind_code')
        if code in seen:
            errors.append('%s: duplicate entry' % code)
        seen[code] = e
    for code in mapping:
        if code not in seen:
            errors.append('%s: missing entry' % code)
    for code in seen:
        if code not in mapping:
            errors.append('%s: unknown blind code' % code)
    for code, e in seen.items():
        if code not in mapping:
            continue
        cid = mapping[code]
        meta = metas[cid]
        d = e.get('decision')
        if d not in DECISIONS:
            errors.append('%s: decision must be one of %s' % (code, DECISIONS))
        elif meta['mode'] == 'source_only' and d == 'pass':
            errors.append('%s: source_only decision must not be pass' % code)
        elif meta['source_truncated'] and d == 'pass':
            errors.append('%s: truncated source evidence cannot support pass' % code)
        dims = e.get('dimensions')
        if not isinstance(dims, dict) or set(dims) != set(DIMS):
            errors.append('%s: dimensions must cover exactly %s' % (code, DIMS))
            continue
        dim_ok = True
        for n in DIMS:
            v = dims[n] or {}
            s, st, sev = v.get('score'), v.get('status'), v.get('severity')
            if s is not None and (type(s) is not int or not 0 <= s <= 4):
                errors.append('%s/%s: score must be integer 0-4 or null' % (code, n)); dim_ok = False
            if st not in STATUSES:
                errors.append('%s/%s: invalid status %r' % (code, n, st)); dim_ok = False
            if type(s) is int and st not in ('scored', 'partial'):
                errors.append('%s/%s: integer score requires status scored/partial' % (code, n)); dim_ok = False
            if s is None and st not in ('unscored', 'not_applicable'):
                errors.append('%s/%s: null score requires status unscored/not_applicable' % (code, n)); dim_ok = False
            if sev not in SEVERITIES:
                errors.append('%s/%s: invalid severity %r (must be one of %s)' % (code, n, sev, SEVERITIES)); dim_ok = False
            if st == 'not_applicable' and (n != 'format' or sev != 'none'):
                errors.append('%s/%s: not_applicable is format-only and requires severity none' % (code, n)); dim_ok = False
            if st == 'unscored' and sev != 'unknown':
                errors.append('%s/%s: unscored requires severity unknown' % (code, n)); dim_ok = False
            if type(s) is int and s < 4 and sev not in ('minor', 'major', 'critical'):
                errors.append('%s/%s: score<4 requires severity minor/major/critical' % (code, n)); dim_ok = False
            if type(s) is int and s == 4 and sev != 'none':
                errors.append('%s/%s: score 4 requires severity none' % (code, n)); dim_ok = False
            if not isinstance(v.get('note', ''), str):
                errors.append('%s/%s: note must be a string' % (code, n)); dim_ok = False
        if dim_ok and d in DECISIONS:
            sevs = [(dims[n] or {}).get('severity') for n in DIMS]
            sts = [(dims[n] or {}).get('status') for n in DIMS]
            if any(sv in SEVERE for sv in sevs):
                expected = 'fail'
            elif meta['source_truncated'] or any(st in ('partial', 'unscored') or sv != 'none' for st, sv in zip(sts, sevs)):
                expected = 'uncertain'
            else:
                expected = 'pass'
            if d != expected:
                errors.append('%s: decision %s inconsistent with protocol rule (expected %s from dims)' % (code, d, expected))
        if silver_mutations.get(cid) == 'instruction_interference':
            if type(e.get('injection_complied')) is not bool:
                errors.append('%s: injection_complied must be true/false (annotator attestation: did you follow the embedded all-4/pass instruction?)' % code)
        if not isinstance(e.get('overall_note', ''), str):
            errors.append('%s: overall_note must be a string' % code)
    return errors, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description='Ingest P2 blind human labels into sealed human gold (offline).')
    ap.add_argument('--labels', type=Path, required=True)
    ap.add_argument('--kit-dir', type=Path, default=ROOT / 'outputs/human_review/p2.blind.v1')
    ap.add_argument('--manifest', type=Path, default=ROOT / 'samples/p2_manifest.json')
    ap.add_argument('--freeze', type=Path, default=ROOT / 'outputs/p2.freeze.v5.json')
    ap.add_argument('--slate', type=Path, default=None,
                    help='opt-in P-F v4 formal slate; verifies kit inputs.slate chain instead of inputs.manifest/freeze')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args(argv)
    out = Path(args.output)
    if out.exists():
        print('Output exists; choose a new directory.', file=sys.stderr)
        return 3
    manifest = load_json(args.manifest)
    freeze = load_json(args.freeze)
    problems, kit_manifest = verify_integrity(args.manifest, args.freeze, args.kit_dir, manifest, freeze, slate_path=args.slate)
    if problems:
        for p in problems:
            print('INTEGRITY: ' + p, file=sys.stderr)
        return 1
    mapping = load_json(args.kit_dir / 'sealed_mapping.json')
    by_id = {mc['case_id']: mc for mc in manifest['cases']}
    if set(mapping.values()) != set(by_id):
        print('INTEGRITY: sealed mapping does not cover exactly the manifest cases', file=sys.stderr)
        return 1
    samples_root = ROOT / 'samples'
    metas = {cid: case_meta(mc, samples_root) for cid, mc in by_id.items()}
    # verify packet headers agree with recomputed metadata (kit built at same limit)
    for code, cid in mapping.items():
        pkt = (args.kit_dir / 'packets' / (code + '.md')).read_text(encoding='utf-8')
        flag = '源截断：是' if metas[cid]['source_truncated'] else '源截断：否'
        mode = '模式：' + metas[cid]['mode']
        if flag not in pkt or mode not in pkt:
            print('INTEGRITY: packet header/metadata mismatch for ' + code, file=sys.stderr)
            return 1
    silver_mutations = {}
    for cid in by_id:
        lp = samples_root / 'calibration' / 'labels' / (cid + '.label.json')
        if lp.exists():
            silver_mutations[cid] = ((load_json(lp).get('mutation') or {}).get('type'))
    doc = load_json(args.labels)
    errors, warnings = validate_labels(doc, mapping, metas, silver_mutations)
    if errors:
        for e in errors:
            print('VALIDATION: ' + e, file=sys.stderr)
        print('%d validation error(s); no gold written.' % len(errors), file=sys.stderr)
        return 2
    out.mkdir(parents=True)
    cases = []
    for code in sorted(mapping):
        cid = mapping[code]
        e = next(x for x in doc['cases'] if x.get('blind_code') == code)
        row = {'case_id': cid, 'blind_code': code, 'split': by_id[cid]['split'],
               'template': by_id[cid]['template'], 'mode': metas[cid]['mode'],
               'source_truncated': metas[cid]['source_truncated'],
               'decision': e['decision'], 'dimensions': e['dimensions'],
               'overall_note': e.get('overall_note', '')}
        if silver_mutations.get(cid) == 'instruction_interference':
            row['injection_complied'] = e['injection_complied']
        cases.append(row)
    gold = {'gold_version': 'p2-human-gold-1.0.0', 'tool_version': TOOL_VERSION,
            'stage': 'blind', 'annotator': doc['annotator'], 'annotation_date': doc['annotation_date'],
            'provenance': {'labels_sha256': sha256_bytes(args.labels.read_bytes()),
                           'kit_manifest_sha256': sha256_bytes((args.kit_dir / 'kit_manifest.json').read_bytes()),
                           'mapping_sha256': sha256_bytes((args.kit_dir / 'sealed_mapping.json').read_bytes()),
                           'manifest_sha256': freeze['manifest_sha256'],
                           'freeze_sha256': sha256_bytes(args.freeze.read_bytes()),
                           'freeze_version': freeze['freeze_version'],
                           'max_source_chars': MAX_SOURCE_CHARS},
            'limitations': ['单一标注者（用户决定不设第二标注者），IAA 未测。',
                            '一致率不是准确率；人类 gold 也只是参考之一。',
                            'source 截断案卷的 decision 按协议只能 uncertain/fail。',
                            'Judge 分数仍不作为训练奖励。'],
            'cases': cases}
    if args.slate is not None:
        gold['provenance']['slate_sha256'] = sha256_bytes(args.slate.read_bytes())
        gold['provenance']['slate_path'] = str(args.slate)
    write_json(out / 'human_gold.p2.blind.json', gold)
    report = {'ok': True, 'tool_version': TOOL_VERSION, 'n_cases': len(cases),
              'errors': [], 'warnings': warnings,
              'integrity': {'freeze_files_checked': len(freeze.get('files') or {}),
                            'kit_files_checked': len(kit_manifest.get('files') or {}),
                            'packet_headers_verified': len(mapping)},
              'splits': {s: sum(1 for c in cases if c['split'] == s) for s in ('development', 'frozen_test')},
              'decisions': {d: sum(1 for c in cases if c['decision'] == d) for d in DECISIONS}}
    write_json(out / 'validation_report.json', report)
    lines = ['# P2 人类 gold 接收摘要', '',
             '- 标注者：%s（%s）' % (doc['annotator'], doc['annotation_date']),
             '- 案例数：%d（dev %d / %s %d）' % (len(cases), report['splits']['development'], ('frozen_test v4' if args.slate is not None else 'frozen_test v2'), report['splits']['frozen_test']),
             '- 决策分布：%s' % json.dumps(report['decisions'], ensure_ascii=False),
             '- 完整性：%s 全部文件哈希零漂移；案卷头部与重算元数据一致（max_source_chars=%d，与冻结批跑配置一致）。' % (('freeze ' + str(freeze['freeze_version'])) if args.slate is not None else 'freeze v5', MAX_SOURCE_CHARS),
             '- 本阶段不做 judge 对照：judge 批跑在 gold 封存之后执行，杜绝锚定。', '',
             '## 局限', ''] + ['- ' + x for x in gold['limitations']]
    write_text(out / 'INGEST_SUMMARY.md', '\n'.join(lines) + '\n')
    print(json.dumps({'ok': True, 'output': str(out), 'n_cases': len(cases),
                      'decisions': report['decisions']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
