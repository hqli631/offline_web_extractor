"""One-shot freeze amendment: node-3 freeze v2 -> v3 (P1 judge v1.1.0).

Judge-layer evidence-contract upgrade in rubrics_judge.py: per-dimension evidence
menus (prompt) + whitespace-folded quote matching (validation tolerance,
hallucination guard unchanged) + probe-only perturbation params; JUDGE_VERSION
1.0.0 -> 1.1.0.

Discovered coupling (pre-registered revision R1, 2026-11-18): each silver label
embeds a build-time 'prompt_chars' diagnostic (the prompt JSON length), and the
freeze snapshots builder output while --verify expects disk == builder == freeze.
Adding evidence menus changes that diagnostic. This amendment PROVES every
rebuilt label differs from its frozen on-disk version ONLY in 'prompt_chars' (all
scoring fields identical), refreshes that diagnostic on disk, updates the v3
cases label_sha256/prompt_chars, and writes freeze v3 so disk == builder == freeze.
Scoring protocol doc, rubrics_v2.py, builder, candidates, gold annotations,
manifest, source pages and batch config are UNCHANGED; silver label scoring
content (expected/mutation/decision/hashes) is proven identical. frozen_test is
not re-run or tuned in P1. Idempotent; refuses to overwrite an existing v3 file.
--dry-run proves without writing. Zero model calls.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.build_calibration_set import ROOT, build_all, dump, sha256_json, _freeze_entries

JUDGE_REL = 'src/webextractor/rubrics_judge.py'
V2_REL = 'outputs/rubrics_judge.node3.freeze.v2.json'
V3_REL = 'outputs/rubrics_judge.node3.freeze.v3.json'
LABEL_PREFIX = 'samples/calibration/labels/'

REASON = ('P1 judge v1.1.0 evidence-contract upgrade in rubrics_judge.py: '
          '(1) per-dimension evidence_menus of exact registry-prefix {ref, quote} '
          'suggestions (deterministic, label-free, budget-aware quote prefix '
          '{120,60,30}); (2) quote matching folds all whitespace runs to single '
          'spaces before the exact-substring check, non-whitespace characters still '
          'verbatim and in order, hallucination guard unchanged; (3) probe-only '
          'source_order_seed/dimension_phrasing params (default None leaves the '
          'production prompt byte-identical). JUDGE_VERSION 1.0.0 -> 1.1.0. '
          'Silver labels embed a build-time prompt_chars diagnostic; menus change it, '
          'so each label is refreshed for prompt_chars ONLY (proven field-identical '
          'otherwise) to keep disk == builder == freeze. Scoring protocol doc, '
          'rubrics_v2.py, builder, candidates, gold, manifest, source pages and batch '
          'config unchanged; silver scoring content unchanged. Pre-registered in '
          'docs/P1_META_EVAL_PLAN.md (revision R1). frozen_test not re-run or tuned.')


def _label_without_diagnostic(label):
    return {k: v for k, v in label.items() if k != 'prompt_chars'}


def compute_amendment(v2_path):
    v2 = json.loads(Path(v2_path).read_text(encoding='utf-8'))
    if v2.get('freeze_version') != 2:
        raise ValueError('Parent freeze must be version 2')
    samples_root = ROOT / 'samples'
    built = build_all(samples_root)
    manifest = {'judge_manifest_version': 1, 'cases': [item['manifest_case'] for item in built]}
    manifest_bytes = dump(manifest).encode('utf-8')
    entries = _freeze_entries(built, samples_root, manifest_bytes)
    old_files, new_files = v2['files'], entries
    if set(old_files) != set(new_files):
        raise ValueError('File set drift; amendment refused')
    changed = [k for k in old_files if old_files[k] != new_files[k]]
    label_changes = [k for k in changed if k.startswith(LABEL_PREFIX)]
    other_changes = [k for k in changed if not k.startswith(LABEL_PREFIX)]
    if other_changes != [JUDGE_REL]:
        raise ValueError('Unexpected non-label changed files: ' + repr(other_changes))
    if sha256_json(manifest) != v2['manifest_sha256']:
        raise ValueError('Manifest drift; amendment refused')
    by_id = {item['case_id']: item for item in built}
    proofs = {}
    new_cases = []
    for row in v2['cases']:
        cid = row['case_id']
        item = by_id[cid]
        if sha256_json(item['candidate']) != row['candidate_sha256']:
            raise ValueError('Candidate data drift: ' + cid)
        label_rel = LABEL_PREFIX + cid + '.label.json'
        disk_label = json.loads((ROOT / label_rel).read_text(encoding='utf-8'))
        rebuilt_label = item['label']
        if _label_without_diagnostic(disk_label) != _label_without_diagnostic(rebuilt_label):
            raise ValueError('Label scoring content drift (beyond prompt_chars): ' + cid)
        if disk_label.get('prompt_chars') != rebuilt_label.get('prompt_chars'):
            proofs[cid] = {'old_prompt_chars': disk_label.get('prompt_chars'),
                           'new_prompt_chars': rebuilt_label.get('prompt_chars')}
        new_row = dict(row)
        new_row['label_sha256'] = sha256_json(rebuilt_label)
        if 'prompt_chars' in new_row:
            new_row['prompt_chars'] = item.get('prompt_chars')
        new_cases.append(new_row)
    v3 = dict(v2)
    v3['freeze_version'] = 3
    v3['generated_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    v3['files'] = entries
    v3['cases'] = new_cases
    v3['amendment'] = {
        'parent_freeze': str(v2_path),
        'parent_freeze_version': 2,
        'reason': REASON,
        'changed_code_files': {JUDGE_REL: {'old_sha256': old_files[JUDGE_REL], 'new_sha256': new_files[JUDGE_REL]}},
        'changed_label_files': label_changes,
        'label_change_kind': 'prompt_chars diagnostic only; refreshed on disk; scoring content proven field-identical',
        'label_prompt_chars_refresh': proofs,
        'candidate_gold_manifest_source_hashes_identical_to_v2': True,
        'scoring_content_unchanged': True,
        'on_disk_silver_labels_modified': True,
        'batch_config_changed': False,
        'judge_version': {'old': '1.0.0', 'new': '1.1.0'},
        'preregistration': 'docs/P1_META_EVAL_PLAN.md',
        'preregistration_revision': 'R1 (prompt_chars diagnostic coupling)',
    }
    return v3, changed, built, proofs


def main(argv=None):
    ap = argparse.ArgumentParser(description='Amend freeze v2 -> v3 (P1 judge v1.1.0).')
    ap.add_argument('--v2', type=Path, default=ROOT / V2_REL)
    ap.add_argument('--output', type=Path, default=ROOT / V3_REL)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args(argv)
    if args.output.exists():
        print('Refusing to overwrite existing freeze v3.', file=sys.stderr)
        return 3
    try:
        v3, changed, built, proofs = compute_amendment(args.v2)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    if args.dry_run:
        print(json.dumps({'dry_run': True, 'changed_files': changed,
                          'code_changed': [JUDGE_REL], 'labels_to_refresh': len(proofs),
                          'files': len(v3['files']), 'cases': len(v3['cases']),
                          'new_judge_sha256': v3['files'][JUDGE_REL]}, ensure_ascii=False))
        return 0
    # Refresh the prompt_chars diagnostic on disk so disk == builder == freeze v3.
    for item in built:
        label_rel = LABEL_PREFIX + item['case_id'] + '.label.json'
        (ROOT / label_rel).write_text(dump(item['label']), encoding='utf-8', newline='')
    args.output.write_text(dump(v3), encoding='utf-8', newline='')
    print(json.dumps({'amendment': 'OK', 'freeze': str(args.output),
                      'code_changed': [JUDGE_REL], 'labels_refreshed': len(proofs),
                      'on_disk_silver_labels_modified': True,
                      'files': len(v3['files']), 'cases': len(v3['cases'])}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
