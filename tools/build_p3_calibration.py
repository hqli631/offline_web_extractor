# -*- coding: utf-8 -*-
"""P3 sealed test v3 builder (zero model calls).

Builds 12 NEW silver cases (2 templates x 6 variants) from the two short real
pages collected under approved route b (2026-11-22 hqli631): p3_npr_text
(npr-text, 14,398 chars) and p3_gnu_essay (gnu-philosophy, 19,271 chars).
Both <= frozen max_source_chars=20000 -> NO truncation -> pass reachable
(pre-registered docs/P3_GATE_PLAN.md section 3). with_gold reference = clean
extraction (assistant_silver, subject to user blind labeling). Reuses
build_case / mutate / derive_expected from build_calibration_set. Produces a
SEPARATE p3 manifest + freeze v7; original freeze v1-v4/v6 and p2.freeze.v5
untouched; frozen_test v1 permanently sealed; v2 consumed, never re-run.
Refuses overwrite; --dry-run builds in memory and reports feasibility.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.build_calibration_set import (ROOT, build_case, check_manifest_isolation,
                                         sha256_bytes, sha256_json, dump,
                                         BATCH_MAX_SOURCE_CHARS, LABEL_ORIGIN)
from src.webextractor.extractor import extract_html

P3_MANIFEST_REL = 'samples/p3_manifest.json'
P3_FREEZE_REL = 'outputs/p3.freeze.v7.json'
VARIANTS = ['clean', 'missing_paragraph', 'noise', 'duplicate', 'reorder', 'instruction_interference']

V3_BASES = [
    {'name': 'p3_npr_text', 'short': 'nprtext', 'lang': 'en',
     'split': 'frozen_test', 'p3_role': 'frozen_test_v3'},
    {'name': 'p3_gnu_essay', 'short': 'gnuessay', 'lang': 'en',
     'split': 'frozen_test', 'p3_role': 'frozen_test_v3'},
]


def _ensure_gold(base, samples_root):
    gold_rel = base['name'] + '.expected.json'
    gp = samples_root / gold_rel
    if not gp.exists():
        sb = (samples_root / (base['name'] + '.html')).read_bytes()
        r = extract_html(sb)
        clean = {'title': r.title, 'blocks': r.to_dict()['blocks']}
        gp.write_text(dump(clean), encoding='utf-8', newline='')
    return gold_rel


def build_v3(dry_run=False):
    samples_root = ROOT / 'samples'
    built = []
    feasible = []
    for base in V3_BASES:
        gold_rel = _ensure_gold(base, samples_root) if not dry_run else (
            base['name'] + '.expected.json' if (samples_root / (base['name'] + '.expected.json')).exists() else None)
        b = dict(base, gold=gold_rel)
        for variant in VARIANTS:
            try:
                item = build_case(b, variant, samples_root)
                built.append(item)
                feasible.append((base['short'], variant, 'ok' if gold_rel else 'source_only'))
            except ValueError as e:
                feasible.append((base['short'], variant, 'SKIP: ' + str(e)[:80]))
    check_manifest_isolation([x['manifest_case'] for x in built])
    return built, feasible


def _freeze_entries_v3(built, samples_root, manifest_bytes):
    entries = {}
    rel = lambda p: str(p.relative_to(ROOT)).replace('\\', '/')
    entries['samples/p3_manifest.json'] = sha256_bytes(manifest_bytes)
    for base in V3_BASES:
        src = samples_root / (base['name'] + '.html')
        entries[rel(src)] = sha256_bytes(src.read_bytes())
        prov = samples_root / (base['name'] + '.html.source.json')
        entries[rel(prov)] = sha256_bytes(prov.read_bytes())
        gp = samples_root / (base['name'] + '.expected.json')
        if gp.exists():
            entries[rel(gp)] = sha256_bytes(gp.read_bytes())
    for item in built:
        cid = item['case_id']
        entries['samples/calibration/' + cid + '.candidate.json'] = sha256_bytes(dump(item['candidate']).encode('utf-8'))
        entries['samples/calibration/labels/' + cid + '.label.json'] = sha256_bytes(dump(item['label']).encode('utf-8'))
    for extra in ('src/webextractor/rubrics_v2.py', 'src/webextractor/rubrics_judge.py',
                  'docs/RUBRICS_V2_PROTOCOL.md', 'tools/build_calibration_set.py',
                  'tools/build_p3_calibration.py', 'tools/collect_p3_sources.py'):
        entries[extra] = sha256_bytes((ROOT / extra).read_bytes())
    return entries


def main(argv=None):
    ap = argparse.ArgumentParser(description='Build P3 sealed test v3 (12 silver cases + freeze v7).')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--manifest', type=Path, default=ROOT / P3_MANIFEST_REL)
    ap.add_argument('--freeze', type=Path, default=ROOT / P3_FREEZE_REL)
    args = ap.parse_args(argv)
    if not args.dry_run and (args.manifest.exists() or args.freeze.exists()):
        print('Refusing to overwrite existing P3 manifest/freeze.', file=sys.stderr)
        return 3
    built, feasible = build_v3(dry_run=args.dry_run)
    from collections import Counter
    splits = Counter(x['manifest_case']['split'] for x in built)
    if args.dry_run:
        print(json.dumps({'dry_run': True, 'n_built': len(built), 'splits': dict(splits),
                          'feasibility': feasible}, ensure_ascii=False))
        return 0
    if len(built) != 12:
        print('Expected 12 cases (2 templates x 6 variants); got %d. Refusing partial freeze.' % len(built),
              file=sys.stderr)
        return 2
    samples_root = ROOT / 'samples'
    for item in built:
        cid = item['case_id']
        (samples_root / 'calibration' / (cid + '.candidate.json')).write_text(dump(item['candidate']), encoding='utf-8', newline='')
        (samples_root / 'calibration' / 'labels' / (cid + '.label.json')).write_text(dump(item['label']), encoding='utf-8', newline='')
    manifest = {'judge_manifest_version': 1, 'cases': [x['manifest_case'] for x in built]}
    manifest_bytes = dump(manifest).encode('utf-8')
    args.manifest.write_text(dump(manifest), encoding='utf-8', newline='')
    entries = _freeze_entries_v3(built, samples_root, manifest_bytes)
    cases_rows = []
    for item in built:
        mc = item['manifest_case']; lab = item['label']
        cases_rows.append({'case_id': item['case_id'], 'split': mc['split'], 'template': mc['template'],
                           'candidate_sha256': lab['candidate_sha256'], 'source_sha256': lab['source_sha256'],
                           'gold_sha256': lab['gold_sha256'], 'label_sha256': sha256_json(lab),
                           'prompt_chars': item['prompt_chars'], 'source_truncated': lab['source_truncated']})
    freeze = {'freeze_version': 7, 'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'batch_config': {'max_source_chars': BATCH_MAX_SOURCE_CHARS, 'max_output_tokens': 2200,
                               'timeout_seconds': 90, 'model': 'qwen3.8-27b'},
              'label_policy': {'label_origin': LABEL_ORIGIN, 'human_reviewed': False,
                               'note': 'P3 v3 silver labels; not human gold. frozen_test v3 scored ONCE after user blind gold; no tuning. frozen_test v1 permanently sealed; v2 consumed in P2.'},
              'counts': {'cases': len(built), 'splits': dict(splits)},
              'manifest_sha256': sha256_json(manifest), 'files': entries, 'cases': cases_rows,
              'p3_note': 'P3 sealed test v3; pre-registered docs/P3_GATE_PLAN.md (approved hqli631 2026-11-22, route b). Sources collected via tools/collect_p3_sources.py with full fetch provenance; both <= 20000 chars (no truncation). Original freezes v1-v4/v6 and p2.freeze.v5 untouched.'}
    args.freeze.write_text(dump(freeze), encoding='utf-8', newline='')
    print(json.dumps({'build': 'OK', 'n_cases': len(built), 'splits': dict(splits),
                      'manifest': str(args.manifest), 'freeze': str(args.freeze)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
