# -*- coding: utf-8 -*-
"""Emit a stability-rerun manifest: a subset view of frozen calibration cases.

No new data is created; every selected case must exist in the node-3 freeze.
Deterministic output (LF, no timestamps). Refuses to overwrite.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

STABILITY_IDS = ['cal-appetite-clean', 'cal-appetite-noise', 'cal-iana-clean',
                 'cal-mdn-clean', 'cal-mdn-code_indent', 'cal-github-noise']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'samples' / 'calibration_manifest.json')
    parser.add_argument('--freeze', type=Path, default=ROOT / 'outputs' / 'rubrics_judge.node3.freeze.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'samples' / 'calibration_stability_manifest.json')
    args = parser.parse_args()
    if args.output.exists():
        print('Output exists; choose a new filename.', file=sys.stderr)
        return 3
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    freeze = json.loads(args.freeze.read_text(encoding='utf-8'))
    frozen_ids = {row['case_id'] for row in freeze['cases']}
    by_id = {case['case_id']: case for case in manifest['cases']}
    selected = []
    for case_id in STABILITY_IDS:
        if case_id not in frozen_ids or case_id not in by_id:
            raise ValueError('Case not in frozen calibration set: ' + case_id)
        selected.append(by_id[case_id])
    out = {'judge_manifest_version': 1, 'cases': selected}
    text = json.dumps(out, ensure_ascii=False, indent=1) + '\n'
    args.output.write_text(text, encoding='utf-8', newline='')
    print(json.dumps({'output': str(args.output), 'cases': STABILITY_IDS,
                      'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest()}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
