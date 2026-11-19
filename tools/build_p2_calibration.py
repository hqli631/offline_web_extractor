"""P2 calibration expansion builder (zero model calls).

Builds NEW silver cases from existing local source pages (no new web collection):
python_interpreter_zh (dev expansion), nasa-voyager-news + w3c_accessibility_intro_zh
(new frozen_test v2, pre-registered sealed). with_gold reference = clean extraction
(assistant_silver, subject to human verification in WP4). Reuses build_case /
mutate / derive_expected from build_calibration_set. Produces a SEPARATE P2
manifest + freeze v5; the original 23-case manifest/freeze (v1-v4) is untouched
and frozen_test v1 remains permanently sealed. Refuses overwrite; --dry-run
builds in memory and reports feasibility without writing.
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

P2_MANIFEST_REL = 'samples/p2_manifest.json'
P2_FREEZE_REL = 'outputs/p2.freeze.v5.json'
VARIANTS = ['clean', 'missing_paragraph', 'noise', 'duplicate', 'reorder', 'instruction_interference']

NEW_BASES = [
    {'name': 'python_interpreter_zh', 'short': 'interpreter', 'lang': 'zh',
     'split': 'development', 'p2_role': 'dev_expansion'},
    {'name': 'nasa-voyager-news.candidate', 'short': 'nasa', 'lang': 'en',
     'split': 'frozen_test', 'p2_role': 'frozen_test_v2'},
    {'name': 'w3c_accessibility_intro_zh', 'short': 'w3ca11y', 'lang': 'zh',
     'split': 'frozen_test', 'p2_role': 'frozen_test_v2'},
]


def _ensure_gold(base, samples_root):
    # with_gold reference = clean extraction (assistant_silver). Create if absent.
    gold_rel = base['name'] + '.expected.json'
    gp = samples_root / gold_rel
    if not gp.exists():
        sb = (samples_root / (base['name'] + '.html')).read_bytes()
        r = extract_html(sb)
        clean = {'title': r.title, 'blocks': r.to_dict()['blocks']}
        gp.write_text(dump(clean), encoding='utf-8', newline='')
    return gold_rel


def build_p2(dry_run=False):
    samples_root = ROOT / 'samples'
    built = []
    feasible = []
    for base in NEW_BASES:
        gold_rel = _ensure_gold(base, samples_root) if not dry_run else (
            base['name'] + '.expected.json' if (samples_root / (base['name'] + '.expected.json')).exists() else None)
        b = dict(base, gold=gold_rel)
        for variant in VARIANTS:
            try:
                item = build_case(b, variant, samples_root)
                built.append(item)
                feasible.append((base['short'], variant, 'ok' if gold_rel else 'source_only'))
            except ValueError as e:
                feasible.append((base['short'], variant, 'SKIP: ' + str(e)[:60]))
    check_manifest_isolation([x['manifest_case'] for x in built])
    return built, feasible


def _freeze_entries_p2(built, samples_root, manifest_bytes):
    entries = {}
    rel = lambda p: str(p.relative_to(ROOT)).replace('\\', '/')
    entries['samples/p2_manifest.json'] = sha256_bytes(manifest_bytes)
    for base in NEW_BASES:
        src = samples_root / (base['name'] + '.html')
        entries[rel(src)] = sha256_bytes(src.read_bytes())
        gp = samples_root / (base['name'] + '.expected.json')
        if gp.exists():
            entries[rel(gp)] = sha256_bytes(gp.read_bytes())
    for item in built:
        cid = item['case_id']
        entries['samples/calibration/' + cid + '.candidate.json'] = sha256_bytes(dump(item['candidate']).encode('utf-8'))
        entries['samples/calibration/labels/' + cid + '.label.json'] = sha256_bytes(dump(item['label']).encode('utf-8'))
    for extra in ('src/webextractor/rubrics_v2.py', 'src/webextractor/rubrics_judge.py',
                  'docs/RUBRICS_V2_PROTOCOL.md', 'tools/build_calibration_set.py', 'tools/build_p2_calibration.py'):
        entries[extra] = sha256_bytes((ROOT / extra).read_bytes())
    return entries


def main(argv=None):
    ap = argparse.ArgumentParser(description='Build P2 expansion calibration (new silver cases + freeze v5).')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--manifest', type=Path, default=ROOT / P2_MANIFEST_REL)
    ap.add_argument('--freeze', type=Path, default=ROOT / P2_FREEZE_REL)
    args = ap.parse_args(argv)
    if not args.dry_run and (args.manifest.exists() or args.freeze.exists()):
        print('Refusing to overwrite existing P2 manifest/freeze.', file=sys.stderr)
        return 3
    built, feasible = build_p2(dry_run=args.dry_run)
    from collections import Counter
    splits = Counter(x['manifest_case']['split'] for x in built)
    if args.dry_run:
        print(json.dumps({'dry_run': True, 'n_built': len(built), 'splits': dict(splits),
                          'feasibility': feasible}, ensure_ascii=False))
        return 0
    samples_root = ROOT / 'samples'
    for item in built:
        cid = item['case_id']
        (samples_root / 'calibration' / (cid + '.candidate.json')).write_text(dump(item['candidate']), encoding='utf-8', newline='')
        (samples_root / 'calibration' / 'labels' / (cid + '.label.json')).write_text(dump(item['label']), encoding='utf-8', newline='')
    manifest = {'judge_manifest_version': 1, 'cases': [x['manifest_case'] for x in built]}
    manifest_bytes = dump(manifest).encode('utf-8')
    args.manifest.write_text(dump(manifest), encoding='utf-8', newline='')
    entries = _freeze_entries_p2(built, samples_root, manifest_bytes)
    cases_rows = []
    for item in built:
        mc = item['manifest_case']; lab = item['label']
        cases_rows.append({'case_id': item['case_id'], 'split': mc['split'], 'template': mc['template'],
                           'candidate_sha256': lab['candidate_sha256'], 'source_sha256': lab['source_sha256'],
                           'gold_sha256': lab['gold_sha256'], 'label_sha256': sha256_json(lab),
                           'prompt_chars': item['prompt_chars'], 'source_truncated': lab['source_truncated']})
    freeze = {'freeze_version': 5, 'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
              'batch_config': {'max_source_chars': BATCH_MAX_SOURCE_CHARS, 'max_output_tokens': 2200,
                               'timeout_seconds': 90, 'model': 'qwen3.8-27b'},
              'label_policy': {'label_origin': LABEL_ORIGIN, 'human_reviewed': False,
                               'note': 'P2 expansion silver labels; not human gold. frozen_test v2 scored once; no tuning on it. frozen_test v1 permanently sealed.'},
              'counts': {'cases': len(built), 'splits': dict(splits)},
              'manifest_sha256': sha256_json(manifest), 'files': entries, 'cases': cases_rows,
              'p2_note': 'P2 expansion; new frozen_test v2 pre-registered sealed; original 23-case freeze v1-v4 untouched.'}
    args.freeze.write_text(dump(freeze), encoding='utf-8', newline='')
    print(json.dumps({'build': 'OK', 'n_cases': len(built), 'splits': dict(splits),
                      'manifest': str(args.manifest), 'freeze': str(args.freeze)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
