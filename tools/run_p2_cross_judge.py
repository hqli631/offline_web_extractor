"""P2 cross-family cross-judge runner (CC Switch OpenAI-compatible, e.g. gpt-5.6-sol).

DESCRIPTIVE cross-judge: same v1.2 judge protocol/prompt as the Qwen judge, but a
different model family via JudgeOpenAIProvider. Reuses run_batch (cache/signature
bind model, so cross-family entries separate from Qwen). Does NOT modify the
production Qwen judge. Model calls require user-approved budget; --dry-run plans
without calling. Output refuses overwrite (exit 3).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.run_rubrics_judge import ROOT, run_batch, load_manifest
from src.webextractor.judge_openai_provider import JudgeOpenAIProvider


def main(argv=None):
    ap = argparse.ArgumentParser(description='P2 cross-family cross-judge (descriptive).')
    ap.add_argument('manifest', type=Path, nargs='?', default=ROOT / 'samples/calibration_manifest.json')
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--model', default='gpt-5.6-sol')
    ap.add_argument('--base-url', default=None)
    ap.add_argument('--split', default='development', choices=('smoke', 'development', 'frozen_test'))
    ap.add_argument('--max-calls', type=int, default=12)
    ap.add_argument('--max-output-tokens', type=int, default=2200)
    ap.add_argument('--max-source-chars', type=int, default=20000)
    ap.add_argument('--timeout', type=float, default=90.0)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args(argv)
    if args.output.exists():
        print('Output exists; choose a new filename.', file=sys.stderr)
        return 3
    manifest = load_manifest(args.manifest)
    n = sum(1 for c in manifest['cases'] if c['split'] == args.split)
    if args.dry_run:
        print(json.dumps({'dry_run': True, 'model': args.model, 'split': args.split,
                          'n_cases': n, 'max_calls': args.max_calls,
                          'base_url': args.base_url or '(env/default)'}, ensure_ascii=False))
        return 0
    provider = JudgeOpenAIProvider(model=args.model, base_url=args.base_url,
                                   timeout_seconds=args.timeout, max_retries=0)
    report = run_batch(args.manifest, provider, model=args.model,
                       max_output_tokens=args.max_output_tokens, max_source_chars=args.max_source_chars,
                       timeout_seconds=args.timeout, max_calls=args.max_calls,
                       split_filter=args.split, report_path=args.output)
    rows = [{'id': r['case_id'], 'status': r['status'],
             'decision': (r['report']['assessment']['decision'] if r.get('report') and r['report'].get('assessment') else None)}
            for r in report['cases']]
    print(json.dumps({'output': str(args.output), 'model': args.model,
                      'new_api_calls': report['new_api_calls'],
                      'usage_new_calls_only': report['usage_new_calls_only'], 'cases': rows}, ensure_ascii=False))
    return 0 if all(r['status'] == 'accepted' for r in report['cases']) else 2


if __name__ == '__main__':
    raise SystemExit(main())
