"""Run the bounded Agent workflow on explicitly declared reference pages."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from .rule_agent import ReplayProvider, run_agent, save_trace

ROOT = Path(__file__).resolve().parents[2]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--provider', choices=('replay', 'ccswitch', 'qwen'), default='replay')
    parser.add_argument('--model', help='Qwen defaults to qwen3.8-27b; CC Switch uses CCSWITCH_MODEL unless overridden')
    parser.add_argument('--replay', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-attempts', type=int, default=3)
    parser.add_argument('--execution-timeout', type=float, default=5.0)
    parser.add_argument('--total-timeout', type=float, default=60.0)
    parser.add_argument('--max-output-tokens', type=int, default=1024)
    args = parser.parse_args()
    if args.provider == 'replay' and args.replay is None:
        parser.error('--replay is required for provider=replay')
    if args.provider != 'replay' and args.replay is not None:
        parser.error('--replay cannot be combined with a network provider')
    if args.provider == 'replay' and args.model is not None:
        parser.error('--model requires a network provider')
    if args.output.exists():
        parser.error('Output exists; choose a new trace filename')
    try:
        manifest = json.loads(args.manifest.read_text(encoding='utf-8-sig'))
        if set(manifest) != {'protocol', 'references'}:
            raise ValueError('Manifest must contain protocol and references only')
        registry = json.loads((ROOT/'samples/sample_registry.json').read_text(encoding='utf-8-sig'))
        reserved = {c['html_sha256'] for c in registry['cases']
                    if c.get('current_role', '').startswith('validation')}
        references = []
        for page in manifest['references']:
            if set(page) != {'id', 'html', 'sha256', 'split'} or page['split'] != 'reference':
                raise ValueError('Reference fields: id, html, sha256, split=reference')
            if page['sha256'] in reserved:
                raise ValueError('Validation snapshot cannot be an Agent reference')
            source = (args.manifest.parent/page['html']).read_bytes()
            digest = hashlib.sha256(source).hexdigest()
            if digest != page['sha256'] or digest in reserved:
                raise ValueError('Source hash mismatch or validation snapshot')
            references.append(dict(id=page['id'], source=source))
        if args.provider == 'replay':
            replay_payload = args.replay.read_bytes()
            provider = ReplayProvider.from_file(args.replay)
        elif args.provider == 'qwen':
            from .qwen_provider import QwenProvider
            provider = QwenProvider(model=args.model or 'qwen3.8-27b', max_retries=0)
        else:
            from .openai_provider import OpenAICompatibleProvider
            provider = OpenAICompatibleProvider(model=args.model, max_retries=0)
        trace = run_agent(references, provider, max_attempts=args.max_attempts,
                          execution_timeout=args.execution_timeout, total_timeout=args.total_timeout,
                          max_output_tokens=args.max_output_tokens)
        trace['manifest_sha256'] = hashlib.sha256(args.manifest.read_bytes()).hexdigest()
        if args.provider == 'replay':
            trace['replay_sha256'] = hashlib.sha256(replay_payload).hexdigest()
        else:
            trace['requested_model'] = provider.model
        trace['implementation_sha256'] = {
            name: hashlib.sha256((ROOT/'src/webextractor'/name).read_bytes()).hexdigest()
            for name in ['agent_rules.py', 'rule_agent.py', 'agent_cli.py', 'extractor.py', 'content_blocks.py']}
        if args.provider == 'ccswitch':
            trace['implementation_sha256']['openai_provider.py'] = hashlib.sha256(
                (ROOT/'src/webextractor/openai_provider.py').read_bytes()).hexdigest()
        elif args.provider == 'qwen':
            trace['implementation_sha256']['qwen_provider.py'] = hashlib.sha256(
                (ROOT/'src/webextractor/qwen_provider.py').read_bytes()).hexdigest()
        save_trace(trace, args.output)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps(dict(status=trace['status'], attempts=len(trace['attempts']),
                         quality_evaluated=trace['quality_evaluated'], output=str(args.output))))
    return 0 if trace['runtime_accepted'] else 2

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
