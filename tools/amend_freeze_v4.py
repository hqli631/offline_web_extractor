"""One-shot freeze amendment: node-3 freeze v3 -> v4 (P1.5 judge v1.2.0).

Judge-layer anti-anchoring decoupling in rubrics_judge.py ONLY: evidence_menus
repositioned as a citation appendix (last prompt key) + a SCORING INDEPENDENCE
constraint (score/severity solely from actual defect magnitude per anchors; menus
must not influence scoring) + severity-anchor reinforcement; JUDGE_VERSION
1.1.0 -> 1.2.0. Menus content, whitespace-folded quote matching, schema, s:/g:
citation rule and probe params are unchanged. General prompt principle, no
case-specific branches.

Same prompt_chars diagnostic coupling as R1: silver labels embed prompt_chars and
the freeze snapshots builder output (--verify expects disk == builder == freeze).
This amendment PROVES every rebuilt label differs from its frozen on-disk version
ONLY in prompt_chars (scoring fields identical), refreshes that diagnostic on disk,
updates v4 cases label_sha256/prompt_chars, writes freeze v4. Scoring protocol doc,
rubrics_v2.py, builder, candidates, gold, manifest, source pages, batch config
UNCHANGED; silver scoring content proven identical. frozen_test not re-run/tuned.
Idempotent; refuses overwrite of existing v4. --dry-run proves without writing.
Zero model calls.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.build_calibration_set import ROOT, build_all, dump, sha256_json, _freeze_entries

JUDGE_REL = 'src/webextractor/rubrics_judge.py'
PARENT_REL = 'outputs/rubrics_judge.node3.freeze.v3.json'
OUTPUT_REL = 'outputs/rubrics_judge.node3.freeze.v4.json'
LABEL_PREFIX = 'samples/calibration/labels/'

REASON = ('P1.5 judge v1.2.0 anti-anchoring decoupling in rubrics_judge.py only: '
          '(1) evidence_menus repositioned as a citation appendix (last prompt key, '
          'after source/candidate/gold); (2) new SCORING INDEPENDENCE constraint — '
          'score and severity determined SOLELY from actual defect magnitude per '
          'anchors, menus are citation convenience only and MUST NOT raise/lower '
          'any score or severity; (3) severity-anchor reinforcement. General prompt '
          'principle, no case-specific branches. Menus content, whitespace-folded '
          'quote matching, schema, s:/g: rule, probe params unchanged. JUDGE_VERSION '
          '1.1.0 -> 1.2.0. Silver labels refreshed for prompt_chars diagnostic ONLY '
          '(proven field-identical otherwise) to keep disk == builder == freeze. '
          'Scoring protocol doc, rubrics_v2.py, builder, candidates, gold, manifest, '
          'source pages, batch config unchanged; silver scoring content unchanged. '
          'Pre-registered in docs/P1_5_META_EVAL_PLAN.md. frozen_test not re-run/tuned.')


def _label_without_diagnostic(label):
    return {k: v for k, v in label.items() if k != 'prompt_chars'}


def compute_amendment(parent_path):
    parent = json.loads(Path(parent_path).read_text(encoding='utf-8'))
    if parent.get('freeze_version') != 3:
        raise ValueError('Parent freeze must be version 3')
    samples_root = ROOT / 'samples'
    built = build_all(samples_root)
    manifest = {'judge_manifest_version': 1, 'cases': [item['manifest_case'] for item in built]}
    manifest_bytes = dump(manifest).encode('utf-8')
    entries = _freeze_entries(built, samples_root, manifest_bytes)
    old_files, new_files = parent['files'], entries
    if set(old_files) != set(new_files):
        raise ValueError('File set drift; amendment refused')
    changed = [k for k in old_files if old_files[k] != new_files[k]]
    label_changes = [k for k in changed if k.startswith(LABEL_PREFIX)]
    other_changes = [k for k in changed if not k.startswith(LABEL_PREFIX)]
    if other_changes != [JUDGE_REL]:
        raise ValueError('Unexpected non-label changed files: ' + repr(other_changes))
    if sha256_json(manifest) != parent['manifest_sha256']:
        raise ValueError('Manifest drift; amendment refused')
    by_id = {item['case_id']: item for item in built}
    proofs = {}
    new_cases = []
    for row in parent['cases']:
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
    child = dict(parent)
    child['freeze_version'] = 4
    child['generated_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    child['files'] = entries
    child['cases'] = new_cases
    child['amendment'] = {
        'parent_freeze': str(parent_path),
        'parent_freeze_version': 3,
        'reason': REASON,
        'changed_code_files': {JUDGE_REL: {'old_sha256': old_files[JUDGE_REL], 'new_sha256': new_files[JUDGE_REL]}},
        'changed_label_files': label_changes,
        'label_change_kind': 'prompt_chars diagnostic only; refreshed on disk; scoring content proven field-identical',
        'label_prompt_chars_refresh': proofs,
        'candidate_gold_manifest_source_hashes_identical_to_v3': True,
        'scoring_content_unchanged': True,
        'on_disk_silver_labels_modified': True,
        'batch_config_changed': False,
        'judge_version': {'old': '1.1.0', 'new': '1.2.0'},
        'preregistration': 'docs/P1_5_META_EVAL_PLAN.md',
    }
    return child, changed, built, proofs


def main(argv=None):
    ap = argparse.ArgumentParser(description='Amend freeze v3 -> v4 (P1.5 judge v1.2.0).')
    ap.add_argument('--parent', type=Path, default=ROOT / PARENT_REL)
    ap.add_argument('--output', type=Path, default=ROOT / OUTPUT_REL)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args(argv)
    if args.output.exists():
        print('Refusing to overwrite existing freeze v4.', file=sys.stderr)
        return 3
    try:
        child, changed, built, proofs = compute_amendment(args.parent)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    if args.dry_run:
        print(json.dumps({'dry_run': True, 'changed_files': changed,
                          'code_changed': [JUDGE_REL], 'labels_to_refresh': len(proofs),
                          'files': len(child['files']), 'cases': len(child['cases']),
                          'new_judge_sha256': child['files'][JUDGE_REL]}, ensure_ascii=False))
        return 0
    for item in built:
        label_rel = LABEL_PREFIX + item['case_id'] + '.label.json'
        (ROOT / label_rel).write_text(dump(item['label']), encoding='utf-8', newline='')
    args.output.write_text(dump(child), encoding='utf-8', newline='')
    print(json.dumps({'amendment': 'OK', 'freeze': str(args.output),
                      'code_changed': [JUDGE_REL], 'labels_refreshed': len(proofs),
                      'on_disk_silver_labels_modified': True,
                      'files': len(child['files']), 'cases': len(child['cases'])}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
