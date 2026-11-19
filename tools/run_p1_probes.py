"""P1 dev-only bias/stability probes (pre-registered docs/P1_META_EVAL_PLAN.md).

DESCRIPTIVE ONLY: probe results are never used for acceptance. Runs three
pre-registered probe configs on fixed development subsets, reusing the frozen
manifest and the batch runner's run_case/cache/signature machinery:
  position  - evidence-position shuffle (source_order_seed=20261118), 6 dev cases
  phrasing  - neutral prompt rephrasing (dimension_phrasing=neutral_v1), 6 dev cases
  stability - production prompt repeat with ignore_cache, 2 dev cases
Probe prompts differ from production (position/phrasing), so cache keys separate
naturally; signature is unchanged. Zero model calls until the user approves the
P1 budget; --dry-run plans without calling. Output refuses overwrite (exit 3).
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.run_rubrics_judge import (ROOT, load_manifest, config_signature, sha256_bytes,
                                     run_case, _build_provider, _write_json)

PROBE_SUBSET = ['cal-appetite-clean', 'cal-appetite-noise', 'cal-appetite-duplicate',
                'cal-blurb-clean', 'cal-blurb-noise', 'cal-iana-noise']
STABILITY_SUBSET = ['cal-appetite-clean', 'cal-blurb-noise']
POSITION_SEED = 20261118
PHRASING_VARIANT = 'neutral_v1'

PROBES = {
    'position': {'probe': {'source_order_seed': POSITION_SEED}, 'subset': PROBE_SUBSET, 'ignore_cache': False},
    'phrasing': {'probe': {'dimension_phrasing': PHRASING_VARIANT}, 'subset': PROBE_SUBSET, 'ignore_cache': False},
    'stability': {'probe': None, 'subset': STABILITY_SUBSET, 'ignore_cache': True},
}


def _assemble_probe(manifest_path, manifest_sha, signature, provider_name, probe_key, cfg,
                    max_calls, made, rows):
    fresh = [r['report']['usage'] for r in rows if r.get('new_api_call') and r.get('report') and r['report'].get('usage')]
    usage = {k: sum(u[k] for u in fresh) for k in ('input_tokens', 'output_tokens', 'total_tokens')} if fresh and all(fresh) else None
    return {'tool': 'run_p1_probes.py', 'manifest': str(manifest_path), 'manifest_sha256': manifest_sha,
            'signature': signature, 'provider': provider_name, 'probe_key': probe_key,
            'probe': cfg['probe'], 'subset': cfg['subset'], 'ignore_cache': cfg['ignore_cache'],
            'max_calls': max_calls, 'new_api_calls': made,
            'cache_hits': sum(bool(r.get('cache_hit')) for r in rows),
            'usage_new_calls_only': usage,
            'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'cases': rows,
            'note': 'DESCRIPTIVE ONLY probe; never used for acceptance. Judge scores are uncalibrated; not human labels, accuracy, or training reward.'}


def run_probe_batch(manifest_path, provider, *, model, probe_key, max_calls=6,
                    max_output_tokens=2200, max_source_chars=20000, timeout_seconds=90.0,
                    cache_path=None, report_path=None):
    cfg = PROBES[probe_key]
    root = manifest_path.resolve().parent
    manifest = load_manifest(manifest_path)
    subset = set(cfg['subset'])
    cases = [c for c in manifest['cases'] if c['case_id'] in subset]
    if len(cases) != len(subset):
        raise ValueError('Probe subset must be fully present in manifest')
    if any(c['split'] != 'development' for c in cases):
        raise ValueError('Probe subset must be development cases only')
    signature = config_signature(model, max_output_tokens, max_source_chars, timeout_seconds)
    manifest_sha = sha256_bytes(manifest_path.read_bytes())
    cache_file = cache_path or manifest_path.with_name(manifest_path.name + '.judge_cache.json')
    cache = json.loads(cache_file.read_text(encoding='utf-8')) if cache_file.exists() else {}
    if not isinstance(cache, dict):
        raise ValueError('Judge cache file must be a JSON object')
    rows, made = [], 0
    for case in cases:
        row = {'case_id': case['case_id'], 'split': case['split'], 'status': 'pending',
               'cache_hit': False, 'new_api_call': False, 'case_meta': None, 'report': None}
        try:
            _key, report, meta, called = run_case(case, root, provider, signature, cache,
                                                  cfg['ignore_cache'], allow_call=made < max_calls,
                                                  probe=cfg['probe'])
            if report is None:
                row.update(status='skipped_budget', case_meta=meta)
            else:
                if called:
                    made += 1
                row.update(status=report['status'], cache_hit=bool(report.get('cached')),
                           new_api_call=called, case_meta=meta, report=report)
        except Exception as error:
            row.update(status='error', error={'type': type(error).__name__, 'detail': str(error)})
        rows.append(row)
        _write_json(cache_file, cache)
        if report_path is not None:
            _write_json(report_path, _assemble_probe(manifest_path, manifest_sha, signature, provider.name,
                                                     probe_key, cfg, max_calls, made, rows))
    return _assemble_probe(manifest_path, manifest_sha, signature, provider.name, probe_key, cfg, max_calls, made, rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description='P1 dev-only descriptive probes (position/phrasing/stability).')
    ap.add_argument('manifest', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--probe', choices=list(PROBES), required=True)
    ap.add_argument('--model', default='qwen3.8-27b')
    ap.add_argument('--max-calls', type=int, default=6)
    ap.add_argument('--max-output-tokens', type=int, default=2200)
    ap.add_argument('--max-source-chars', type=int, default=20000)
    ap.add_argument('--timeout', type=float, default=90.0)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args(argv)
    if args.output.exists():
        print('Output exists; choose a new filename.', file=sys.stderr)
        return 3
    cfg = PROBES[args.probe]
    manifest = load_manifest(args.manifest)
    subset = set(cfg['subset'])
    cases = [c for c in manifest['cases'] if c['case_id'] in subset]
    if len(cases) != len(subset) or any(c['split'] != 'development' for c in cases):
        print('Probe subset must be development cases fully present in manifest.', file=sys.stderr)
        return 2
    if args.dry_run:
        print(json.dumps({'dry_run': True, 'probe': args.probe, 'config': cfg,
                          'n_cases': len(cases), 'max_calls': args.max_calls,
                          'model': args.model}, ensure_ascii=False))
        return 0
    provider = _build_provider(args.model, args.timeout)
    report = run_probe_batch(args.manifest, provider, model=args.model, probe_key=args.probe,
                             max_calls=args.max_calls, max_output_tokens=args.max_output_tokens,
                             max_source_chars=args.max_source_chars, timeout_seconds=args.timeout,
                             report_path=args.output)
    rows = [{'id': r['case_id'], 'status': r['status'], 'cache': r['cache_hit'],
             'decision': (r['report']['assessment']['decision'] if r.get('report') and r['report'].get('assessment') else None)}
            for r in report['cases']]
    print(json.dumps({'output': str(args.output), 'probe': args.probe,
                      'new_api_calls': report['new_api_calls'],
                      'usage_new_calls_only': report['usage_new_calls_only'], 'cases': rows}, ensure_ascii=False))
    return 0 if all(r['status'] == 'accepted' for r in report['cases']) else 2


if __name__ == '__main__':
    raise SystemExit(main())
