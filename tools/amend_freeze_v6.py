"""One-shot freeze amendment: node-3 freeze v4 -> v6 (P3 judge v1.3.0).

P3 calibration amendment in rubrics_judge.py ONLY, pre-registered in
docs/P3_AMENDMENT_PROPOSAL.md and approved by hqli631 on 2026-11-22:
(1) anchors '3'/'2' granularity examples (single short noise block in a long
article / one non-lead paragraph missing / single adjacent swap -> 3;
multi-block noise / lead-or-multiple missing / multi-block order loss -> 2);
(2) three general constraints: severity granularity principle, source
presence is not justification for boilerplate inclusion, explicit order
check. Injection handling and duplicate classification UNCHANGED (findings
A/C06 judge_correct). No case-specific rules. JUDGE_VERSION 1.2.0 -> 1.3.0;
RUBRICS 2.0.0 unchanged; batch_config unchanged.

Same prompt_chars diagnostic coupling as v4: original calibration silver
labels are rebuilt and PROVEN to differ from frozen v4 only in prompt_chars
(scoring fields identical), refreshed on disk, v6 cases label_sha256/
prompt_chars updated. P2 silver labels (cal-interpreter/nasa/w3ca11y under
p2.freeze.v5) are INTENTIONALLY NOT refreshed: they are historical artifacts
of the consumed P2 evaluation and keep their v1.2-era prompt_chars
diagnostic; p2.freeze.v5 remains the valid historical record. The v1.3 dev
run builds prompts fresh at runtime; silver labels serve only as mutation
context for scoring. frozen_test v1 sealed; v2 consumed, never re-run.
Idempotent; refuses overwrite of existing v6. --dry-run proves without
writing. Zero model calls.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.build_calibration_set import ROOT, build_all, dump, sha256_json, _freeze_entries

JUDGE_REL = 'src/webextractor/rubrics_judge.py'
PARENT_REL = 'outputs/rubrics_judge.node3.freeze.v4.json'
OUTPUT_REL = 'outputs/rubrics_judge.node3.freeze.v6.json'
LABEL_PREFIX = 'samples/calibration/labels/'

REASON = ('P3 judge v1.3.0 calibration amendment in rubrics_judge.py only, '
          'pre-registered in docs/P3_AMENDMENT_PROPOSAL.md (approved hqli631 '
          '2026-11-22): (1) anchors 3/2 granularity examples (single short '
          'noise block in a long article / one non-lead body paragraph missing '
          '/ single adjacent swap -> 3; multi-block noise or substantial share '
          'of a short article / lead-or-multiple paragraphs missing / '
          'multi-block order disruption -> 2); (2) three general constraints: '
          'severity granularity principle; source presence is not justification '
          'for nav/share/subscribe/feedback/footer inclusion; explicit order '
          'check vs gold/source. Injection handling and duplicate classification '
          'unchanged. No case-specific rules. JUDGE_VERSION 1.2.0 -> 1.3.0; '
          'RUBRICS 2.0.0 and batch_config unchanged. Original calibration silver '
          'labels refreshed for prompt_chars diagnostic ONLY (proven '
          'field-identical otherwise). P2 silver labels (freeze v5) intentionally '
          'NOT refreshed: historical v1.2-era diagnostics of the consumed P2 '
          'evaluation; p2.freeze.v5 remains the valid historical record. '
          'frozen_test v1 sealed; v2 consumed one-shot, not re-run/tuned.')


def _label_without_diagnostic(label):
    return {k: v for k, v in label.items() if k != 'prompt_chars'}


def compute_amendment(parent_path):
    parent = json.loads(Path(parent_path).read_text(encoding='utf-8'))
    if parent.get('freeze_version') != 4:
        raise ValueError('Parent freeze must be version 4')
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
    child['freeze_version'] = 6
    child['generated_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    child['files'] = entries
    child['cases'] = new_cases
    child['amendment'] = {
        'parent_freeze': str(parent_path),
        'parent_freeze_version': 4,
        'reason': REASON,
        'changed_code_files': {JUDGE_REL: {'old_sha256': old_files[JUDGE_REL], 'new_sha256': new_files[JUDGE_REL]}},
        'changed_label_files': label_changes,
        'label_change_kind': 'prompt_chars diagnostic only; refreshed on disk; scoring content proven field-identical',
        'label_prompt_chars_refresh': proofs,
        'p2_silver_labels_refreshed': False,
        'p2_silver_labels_note': 'cal-interpreter/nasa/w3ca11y labels under p2.freeze.v5 keep v1.2-era prompt_chars; historical record of consumed P2 evaluation, intentionally untouched',
        'candidate_gold_manifest_source_hashes_identical_to_v4': True,
        'scoring_content_unchanged': True,
        'on_disk_silver_labels_modified': True,
        'batch_config_changed': False,
        'judge_version': {'old': '1.2.0', 'new': '1.3.0'},
        'preregistration': 'docs/P3_AMENDMENT_PROPOSAL.md',
        'approval': {'by': 'hqli631', 'at': '2026-11-22',
                     'quote': '批准修订；批准阈值；v3 选 b 含采集；批准预算'},
    }
    return child, changed, built, proofs


def main(argv=None):
    ap = argparse.ArgumentParser(description='Amend freeze v4 -> v6 (P3 judge v1.3.0).')
    ap.add_argument('--parent', type=Path, default=ROOT / PARENT_REL)
    ap.add_argument('--output', type=Path, default=ROOT / OUTPUT_REL)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args(argv)
    if args.output.exists():
        print('Refusing to overwrite existing freeze v6.', file=sys.stderr)
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
