# -*- coding: utf-8 -*-
"""One-shot rollback freeze: v6 (failed judge v1.3.0) -> v8 (restored v1.2.0).

Pre-registered consequence (docs/P3_AMENDMENT_PROPOSAL.md section 3, approved
2026-11-22): the v1.3 dev-pool regression guard FAILED (severe_miss_count=3
> 1 on cal-appetite-noise / cal-blurb-noise / cal-blurb-reorder; evidence
outputs/p3.devguard.v1). The amendment is rolled back to v1.2.0 and reported
honestly -- no score chasing, no gold rewrite, no frozen_test re-tuning.

The judge file must ALREADY be restored byte-exact to freeze v4's sha
(edd841ef...) before running this tool. The tool rebuilds silver labels
under the restored v1.2 prompt, PROVES they differ from v6 only in
prompt_chars, and PROVES the resulting file hash set equals freeze v4
exactly (full restoration). Freeze v8 = v4 content + rollback amendment
record. v1.3 artifacts (freeze v6, dev batches, 4 partial v3 evaluations)
remain archived as amendment-failure evidence; the 4 v3 cases evaluated
under v1.3 are EXCLUDED from gate scoring pending the user's path decision.
Refuses overwrite; --dry-run proves without writing. Zero model calls.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.build_calibration_set import ROOT, build_all, dump, sha256_json, _freeze_entries

JUDGE_REL = 'src/webextractor/rubrics_judge.py'
PARENT_REL = 'outputs/rubrics_judge.node3.freeze.v6.json'
RESTORE_REL = 'outputs/rubrics_judge.node3.freeze.v4.json'
OUTPUT_REL = 'outputs/rubrics_judge.node3.freeze.v8.json'
LABEL_PREFIX = 'samples/calibration/labels/'

REASON = ('P3 rollback: judge v1.3.0 amendment FAILED the pre-registered dev '
          'regression guard (docs/P3_AMENDMENT_PROPOSAL.md section 3): '
          'severe_miss_count=3 > 1 (cal-appetite-noise, cal-blurb-noise, '
          'cal-blurb-reorder; granularity anchors downgraded severity below '
          'P0-adjudicated gold). reject_rate 0% and false_alarm 0.0556 passed; '
          'orig dev12 match dropped 0.9167 -> 0.75, kappa 0.8554 -> 0.5443. '
          'Evidence: outputs/p3.devguard.v1. Restored judge v1.2.0 byte-exact '
          '(sha edd841ef... == freeze v4). No gold rewrite, no score chasing. '
          'v1.3 artifacts archived (freeze v6, p3.dev.* batches); 4 v3 cases '
          'evaluated under v1.3 excluded from gate pending user path decision.')


def _label_without_diagnostic(label):
    return {k: v for k, v in label.items() if k != 'prompt_chars'}


def compute_rollback(parent_path, restore_path):
    parent = json.loads(Path(parent_path).read_text(encoding='utf-8'))
    restore = json.loads(Path(restore_path).read_text(encoding='utf-8'))
    if parent.get('freeze_version') != 6:
        raise ValueError('Parent freeze must be version 6 (failed v1.3)')
    if restore.get('freeze_version') != 4:
        raise ValueError('Restore reference must be freeze version 4')
    disk_sha = __import__('hashlib').sha256((ROOT / JUDGE_REL).read_bytes()).hexdigest()
    if disk_sha != restore['files'][JUDGE_REL]:
        raise ValueError('Judge file not restored to freeze v4 sha; restore it byte-exact first')
    samples_root = ROOT / 'samples'
    built = build_all(samples_root)
    manifest = {'judge_manifest_version': 1, 'cases': [item['manifest_case'] for item in built]}
    manifest_bytes = dump(manifest).encode('utf-8')
    entries = _freeze_entries(built, samples_root, manifest_bytes)
    if entries != restore['files']:
        diff = [k for k in entries if entries.get(k) != restore['files'].get(k)]
        raise ValueError('Restored file hashes differ from freeze v4: ' + repr(diff))
    if sha256_json(manifest) != parent['manifest_sha256']:
        raise ValueError('Manifest drift; rollback refused')
    by_id = {item['case_id']: item for item in built}
    proofs = {}
    for row in parent['cases']:
        cid = row['case_id']
        item = by_id[cid]
        if sha256_json(item['candidate']) != row['candidate_sha256']:
            raise ValueError('Candidate data drift: ' + cid)
        disk_label = json.loads((ROOT / (LABEL_PREFIX + cid + '.label.json')).read_text(encoding='utf-8'))
        rebuilt_label = item['label']
        if _label_without_diagnostic(disk_label) != _label_without_diagnostic(rebuilt_label):
            raise ValueError('Label scoring content drift (beyond prompt_chars): ' + cid)
        if disk_label.get('prompt_chars') != rebuilt_label.get('prompt_chars'):
            proofs[cid] = {'v13_prompt_chars': disk_label.get('prompt_chars'),
                           'restored_prompt_chars': rebuilt_label.get('prompt_chars')}
    child = dict(restore)
    child['freeze_version'] = 8
    child['generated_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    child['amendment'] = {
        'type': 'rollback',
        'parent_freeze': str(parent_path),
        'parent_freeze_version': 6,
        'restored_from': str(restore_path),
        'restored_from_version': 4,
        'reason': REASON,
        'judge_version': {'failed': '1.3.0', 'restored': '1.2.0'},
        'failed_judge_sha256': parent['files'][JUDGE_REL],
        'restored_judge_sha256': disk_sha,
        'file_hashes_equal_freeze_v4': True,
        'label_prompt_chars_restore': proofs,
        'scoring_content_unchanged': True,
        'batch_config_changed': False,
        'preregistration': 'docs/P3_AMENDMENT_PROPOSAL.md#3',
        'guard_evidence': 'outputs/p3.devguard.v1/p3.dev.guard.json',
        'v3_partial_consumption': '4 v3 cases evaluated under failed v1.3 (outputs/p3.judge.v1.json); archived, excluded from gate pending user path decision',
        'approval': {'by': 'hqli631', 'at': '2026-11-22',
                     'quote': '批准修订；批准阈值；v3 选 b 含采集；批准预算',
                     'note': 'rollback is the pre-registered consequence of GUARD_FAIL, not a new decision'},
    }
    return child, built, proofs


def main(argv=None):
    ap = argparse.ArgumentParser(description='Rollback freeze v6 -> v8 (restore judge v1.2.0).')
    ap.add_argument('--parent', type=Path, default=ROOT / PARENT_REL)
    ap.add_argument('--restore-ref', type=Path, default=ROOT / RESTORE_REL)
    ap.add_argument('--output', type=Path, default=ROOT / OUTPUT_REL)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args(argv)
    if args.output.exists():
        print('Refusing to overwrite existing freeze v8.', file=sys.stderr)
        return 3
    try:
        child, built, proofs = compute_rollback(args.parent, args.restore_ref)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    if args.dry_run:
        print(json.dumps({'dry_run': True, 'file_hashes_equal_v4': True,
                          'labels_to_restore': len(proofs), 'cases': len(child['cases']),
                          'restored_judge_sha256': child['files'][JUDGE_REL]}, ensure_ascii=False))
        return 0
    for item in built:
        (ROOT / (LABEL_PREFIX + item['case_id'] + '.label.json')).write_text(
            dump(item['label']), encoding='utf-8', newline='')
    args.output.write_text(dump(child), encoding='utf-8', newline='')
    print(json.dumps({'rollback': 'OK', 'freeze': str(args.output),
                      'labels_restored': len(proofs), 'file_hashes_equal_v4': True,
                      'cases': len(child['cases'])}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
