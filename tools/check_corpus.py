"""Check inventory hashes and preserved gold/report identity without extraction."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    registry = json.loads((ROOT / 'samples/sample_registry.json').read_text(encoding='utf-8'))
    errors = []
    rows = []
    for case in registry['cases']:
        try:
            snapshot = ROOT / 'samples' / case['html']
            source = json.loads((ROOT / 'samples' / case['source']).read_text(encoding='utf-8'))
            if digest(snapshot) != case['html_sha256'] or digest(snapshot) != source['sha256']:
                raise ValueError('HTML hash differs from inventory or source record')
            expected = None
            if case.get('expected'):
                path = ROOT / 'samples' / case['expected']
                if digest(path) != case['expected_sha256']:
                    raise ValueError('Expected hash differs from inventory')
                expected = json.loads(path.read_text(encoding='utf-8-sig'))
            if case.get('first_report'):
                report = json.loads((ROOT / case['first_report']).read_text(encoding='utf-8'))
                if report['expected'] != expected:
                    raise ValueError('First report embeds a different expected version')
            if case['current_role'] == 'validation_reserved' and case['prediction_started']:
                raise ValueError('Reserved validation already has a prediction')
            if case['current_role'] == 'validation_scored':
                if case.get('tuning_used') or not case.get('first_report'):
                    raise ValueError('Scored validation lacks first report or was used for tuning')
                release = json.loads((ROOT / case['release_snapshot']).read_text(encoding='utf-8'))
                if release['validation_html_sha256'] != digest(snapshot):
                    raise ValueError('Validation HTML differs from release freeze')
                if release['validation_expected_sha256'] != case['expected_sha256']:
                    raise ValueError('Validation gold differs from release freeze')
            rows.append({'id': case['id'], 'role': case['current_role'], 'ok': True})
        except Exception as error:
            errors.append({'id': case['id'], 'error': str(error)})
    freeze_path = ROOT / 'baselines/rules-gate2-first-pass/manifest.json'
    if freeze_path.exists():
        freeze = json.loads(freeze_path.read_text(encoding='utf-8'))
        for name, expected_hash in freeze['source_sha256'].items():
            if digest(freeze_path.parent / name) != expected_hash:
                errors.append({'snapshot': name, 'error': 'Frozen source bytes changed'})
    result = {'cases': rows, 'roles': dict(Counter(r['role'] for r in rows)), 'errors': errors,
              'note': 'Checks file identity and declared roles only; does not prove human gold quality or chronology. No extractor run.'}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(errors))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
