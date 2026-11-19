"""One-shot freeze amendment: node-3 freeze v1 -> v2.

Reason: narrow validator relaxation in rubrics_judge.py (empty reason tolerated
only for unscored/not_applicable). Prompt, JUDGE_VERSION, batch config, builder,
calibration data and labels are UNCHANGED. This script rebuilds the calibration
set in memory, recomputes freeze entries, asserts the ONLY changed file hash is
src/webextractor/rubrics_judge.py, and writes freeze v2 with amendment metadata.
It refuses to overwrite an existing v2 file.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.build_calibration_set import ROOT, build_all, dump, sha256_json, _freeze_entries

JUDGE_REL = 'src/webextractor/rubrics_judge.py'

def main():
    v1_path = ROOT / 'outputs' / 'rubrics_judge.node3.freeze.json'
    v2_path = ROOT / 'outputs' / 'rubrics_judge.node3.freeze.v2.json'
    if v2_path.exists():
        print('Refusing to overwrite existing freeze v2.', file=sys.stderr)
        return 3
    v1 = json.loads(v1_path.read_text(encoding='utf-8'))
    samples_root = ROOT / 'samples'
    built = build_all(samples_root)
    manifest = {'judge_manifest_version': 1, 'cases': [item['manifest_case'] for item in built]}
    manifest_bytes = dump(manifest).encode('utf-8')
    entries = _freeze_entries(built, samples_root, manifest_bytes)
    old_files, new_files = v1['files'], entries
    if set(old_files) != set(new_files):
        print('File set drift; amendment refused.', file=sys.stderr)
        return 2
    changed = [k for k in old_files if old_files[k] != new_files[k]]
    if changed != [JUDGE_REL]:
        print('Unexpected changed files: ' + repr(changed), file=sys.stderr)
        return 2
    if sha256_json(manifest) != v1['manifest_sha256']:
        print('Manifest drift; amendment refused.', file=sys.stderr)
        return 2
    by_id = {item['case_id']: item for item in built}
    for row in v1['cases']:
        item = by_id[row['case_id']]
        if sha256_json(item['candidate']) != row['candidate_sha256'] or sha256_json(item['label']) != row['label_sha256']:
            print('Case data drift: ' + row['case_id'], file=sys.stderr)
            return 2
    v2 = dict(v1)
    v2['freeze_version'] = 2
    v2['generated_at'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    v2['files'] = entries
    v2['amendment'] = {
        'parent_freeze': 'outputs/rubrics_judge.node3.freeze.json',
        'parent_freeze_version': 1,
        'reason': ('Validator relaxation in rubrics_judge.py: empty reason accepted only for '
                   'unscored/not_applicable dimensions (scored/partial still require non-empty '
                   'reason <=1200 chars). Prompt text, JUDGE_VERSION 1.0.0, batch config, '
                   'builder and all calibration data/labels unchanged; cached provider '
                   'responses revalidate under the amended validator.'),
        'changed_files': {JUDGE_REL: {'old_sha256': old_files[JUDGE_REL], 'new_sha256': new_files[JUDGE_REL]}},
        'data_hashes_identical_to_v1': True,
        'batch_config_changed': False,
    }
    v2_path.write_text(dump(v2), encoding='utf-8', newline='')
    print(json.dumps({'amendment': 'OK', 'freeze': str(v2_path.relative_to(ROOT)),
                      'changed_files': changed, 'files': len(entries), 'cases': len(v2['cases'])}, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
