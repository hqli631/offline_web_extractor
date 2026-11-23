# -*- coding: utf-8 -*-
"""P-F sealed test v4 FORMAL builder (route A, zero model calls).

Builds 12 NEW silver cases (2 never-exposed templates x 6 variants, v3 shape)
from the two short real pages collected under approved route A (2026-11-23
hqli631, tools/collect_pf_v4_sources.py). Requires BOTH samples/pf_v4_*.html
with .source.json provenance sidecars; raw <= 20000 chars -> no truncation ->
pass reachable. with_gold reference = clean extraction (assistant_silver,
subject to user blind labeling; human gold sealed BEFORE any v1.4 judge call).
Produces samples/pf_v4_manifest.json + outputs/pf.freeze.v1.json (chains
pf.protocol.v1 + pb.freeze.v9) + a FORMAL slate for the blind kit. Option B
draft (iana) is superseded, never deleted. Refuses overwrite; --dry-run.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_calibration_set import (build_case, check_manifest_isolation,
                                         sha256_bytes, sha256_json, dump,
                                         BATCH_MAX_SOURCE_CHARS, LABEL_ORIGIN)
from src.webextractor.extractor import extract_html

MANIFEST_REL = 'samples/pf_v4_manifest.json'
FREEZE_REL = 'outputs/pf.freeze.v1.json'
SLATE_REL = 'outputs/pf.v4.slate.v2/pf_v4_slate.formal.json'
COLLECTION_LOG_REL = 'outputs/pf.collection.v1.log.json'
VARIANTS = ['clean', 'missing_paragraph', 'noise', 'duplicate', 'reorder', 'instruction_interference']


def discover_bases(samples_root):
    pages = sorted(p for p in samples_root.glob('pf_v4_*.html')
                   if (samples_root / (p.name + '.source.json')).exists())
    if len(pages) != 2:
        raise ValueError('Route A requires exactly 2 collected pf_v4 pages with provenance sidecars; found %d' % len(pages))
    bases = []
    for p in pages:
        side = json.loads((samples_root / (p.name + '.source.json')).read_text(encoding='utf-8'))
        bases.append({'name': p.stem, 'short': p.stem.replace('pf_v4_', ''), 'lang': 'en',
                      'split': 'frozen_test', 'pf_role': 'frozen_test_v4',
                      'template_family': side['template'], 'collection_url': side['url']})
    fams = [b['template_family'] for b in bases]
    if len(set(fams)) != 2:
        raise ValueError('The two pages must come from different template families; got %s' % fams)
    return bases


def _ensure_gold(base, samples_root):
    gold_rel = base['name'] + '.expected.json'
    gp = samples_root / gold_rel
    if not gp.exists():
        sb = (samples_root / (base['name'] + '.html')).read_bytes()
        r = extract_html(sb)
        clean = {'title': r.title, 'blocks': r.to_dict()['blocks']}
        gp.write_text(dump(clean), encoding='utf-8', newline='')
    return gold_rel


def build_v4(dry_run=False, samples_root=None):
    samples_root = Path(samples_root) if samples_root else ROOT / 'samples'
    bases = discover_bases(samples_root)
    built, feasible = [], []
    for base in bases:
        gold_rel = _ensure_gold(base, samples_root) if not dry_run else (
            base['name'] + '.expected.json' if (samples_root / (base['name'] + '.expected.json')).exists() else None)
        b = dict(base, gold=gold_rel)
        for variant in VARIANTS:
            try:
                item = build_case(b, variant, samples_root)
                item['exposure'] = 'never-exposed new template (route A collection 2026-11-23); family: ' + base['template_family']
                built.append(item)
                feasible.append((base['short'], variant, 'ok'))
            except ValueError as e:
                feasible.append((base['short'], variant, 'SKIP: ' + str(e)[:80]))
    check_manifest_isolation([x['manifest_case'] for x in built])
    return bases, built, feasible


def _freeze_entries(bases, built, samples_root, manifest_bytes):
    entries = {}
    rel = lambda p: str(p.relative_to(ROOT)).replace('\\', '/')
    entries[MANIFEST_REL] = sha256_bytes(manifest_bytes)
    for base in bases:
        for suffix in ('.html', '.html.source.json', '.expected.json'):
            p = samples_root / (base['name'] + suffix)
            if p.exists():
                entries[rel(p)] = sha256_bytes(p.read_bytes())
    for item in built:
        cid = item['case_id']
        entries['samples/calibration/' + cid + '.candidate.json'] = sha256_bytes(dump(item['candidate']).encode('utf-8'))
        entries['samples/calibration/labels/' + cid + '.label.json'] = sha256_bytes(dump(item['label']).encode('utf-8'))
    for extra in ('src/webextractor/rubrics_v2.py', 'src/webextractor/rubrics_judge.py',
                  'src/webextractor/rubrics_judge_v14.py', 'docs/RUBRICS_V2_PROTOCOL.md',
                  'tools/build_calibration_set.py', 'tools/build_pf_v4_calibration.py',
                  'tools/collect_pf_v4_sources.py', 'outputs/pf.protocol.v1.json',
                  'outputs/pf.gate.config.v1.json'):
        entries[extra] = sha256_bytes((ROOT / extra).read_bytes())
    logp = ROOT / COLLECTION_LOG_REL
    if logp.exists():
        entries[COLLECTION_LOG_REL] = sha256_bytes(logp.read_bytes())
    return entries


def main(argv=None):
    ap = argparse.ArgumentParser(description='Build P-F sealed test v4 FORMAL (route A, 12 silver cases + freeze).')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--manifest', type=Path, default=ROOT / MANIFEST_REL)
    ap.add_argument('--freeze', type=Path, default=ROOT / FREEZE_REL)
    ap.add_argument('--slate', type=Path, default=ROOT / SLATE_REL)
    ap.add_argument('--samples-root', type=Path, default=ROOT / 'samples')
    args = ap.parse_args(argv)
    if not args.dry_run and (args.manifest.exists() or args.freeze.exists() or args.slate.exists()):
        print('Refusing to overwrite existing v4 manifest/freeze/slate.', file=sys.stderr)
        return 3
    try:
        bases, built, feasible = build_v4(dry_run=args.dry_run, samples_root=args.samples_root)
    except ValueError as e:
        print('BUILD: ' + str(e), file=sys.stderr)
        return 2
    splits = Counter(x['manifest_case']['split'] for x in built)
    if args.dry_run:
        print(json.dumps({'dry_run': True, 'n_built': len(built), 'splits': dict(splits),
                          'feasibility': feasible}, ensure_ascii=False))
        return 0
    if len(built) != 12:
        print('Expected 12 cases (2 templates x 6 variants); got %d. Refusing partial freeze.' % len(built), file=sys.stderr)
        return 2
    samples_root = Path(args.samples_root)
    for item in built:
        cid = item['case_id']
        (samples_root / 'calibration' / (cid + '.candidate.json')).write_text(dump(item['candidate']), encoding='utf-8', newline='')
        (samples_root / 'calibration' / 'labels' / (cid + '.label.json')).write_text(dump(item['label']), encoding='utf-8', newline='')
    manifest = {'judge_manifest_version': 1, 'cases': [x['manifest_case'] for x in built]}
    manifest_bytes = dump(manifest).encode('utf-8')
    args.manifest.write_text(dump(manifest), encoding='utf-8', newline='')
    entries = _freeze_entries(bases, built, samples_root, manifest_bytes)
    cases_rows = []
    for item in built:
        mc = item['manifest_case']; lab = item['label']
        cases_rows.append({'case_id': item['case_id'], 'split': mc['split'], 'template': mc['template'],
                           'candidate_sha256': lab['candidate_sha256'], 'source_sha256': lab['source_sha256'],
                           'gold_sha256': lab['gold_sha256'], 'label_sha256': sha256_json(lab),
                           'prompt_chars': item['prompt_chars'], 'source_truncated': lab['source_truncated']})
    freeze = {'freeze_version': 'pf-1',
              'batch_config': {'model': 'qwen3.8-27b', 'judge_version': '1.4.0', 'rubrics_version': '2.0.0',
                               'max_source_chars': BATCH_MAX_SOURCE_CHARS, 'max_output_tokens': 2200, 'timeout_seconds': 90},
              'label_policy': {'label_origin': LABEL_ORIGIN, 'human_reviewed': False,
                               'note': 'P-F v4 silver labels; not human gold. frozen_test v4 scored ONCE after user blind gold seal; no tuning. v1/v2/v3 never re-run.'},
              'counts': {'cases': len(built), 'splits': dict(splits)},
              'manifest_sha256': sha256_json(manifest), 'files': entries, 'cases': cases_rows,
              'chain': {'protocol_pin_sha256': sha256_bytes((ROOT / 'outputs/pf.protocol.v1.json').read_bytes()),
                        'pb_freeze_v9_sha256': sha256_bytes((ROOT / 'outputs/pb.freeze.v9.json').read_bytes())},
              'pf_note': 'P-F sealed test v4 FORMAL (route A, approved hqli631 2026-11-23). Sources: tools/collect_pf_v4_sources.py with full fetch provenance; both <= 20000 chars (no truncation). Option B iana draft superseded. Human gold sealed BEFORE judge.'}
    args.freeze.write_text(dump(freeze), encoding='utf-8', newline='')
    slate = {'slate_version': 'pf-v4-slate-formal-1', 'status': 'FORMAL_ROUTE_A_APPROVED',
             'route': 'A', 'approved_by': 'hqli631', 'approved_at': '2026-11-23',
             'manifest_sha256': sha256_bytes(manifest_bytes),
             'freeze_sha256': sha256_bytes(args.freeze.read_bytes()),
             'cases': [{'case_id': x['case_id'], 'manifest_case': x['manifest_case'],
                        'candidate': x['candidate'], 'label': x['label'],
                        'prompt_chars': x['prompt_chars'], 'exposure': x['exposure']} for x in built]}
    args.slate.parent.mkdir(parents=True, exist_ok=True)
    args.slate.write_text(dump(slate), encoding='utf-8', newline='')
    print(json.dumps({'build': 'OK', 'n_cases': len(built), 'splits': dict(splits),
                      'manifest': str(args.manifest), 'freeze': str(args.freeze),
                      'slate': str(args.slate)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
