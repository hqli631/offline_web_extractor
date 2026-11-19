"""Run one bounded CC Switch Agent evaluation with reference/test isolation."""
from __future__ import annotations
import argparse, hashlib, json, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.webextractor.agent_evaluation import evaluate_agent
from src.webextractor.openai_provider import OpenAICompatibleProvider

def main():
    p=argparse.ArgumentParser()
    p.add_argument('manifest', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--max-attempts', type=int, default=2)
    p.add_argument('--total-timeout', type=float, default=90.0)
    p.add_argument('--max-output-tokens', type=int, default=512)
    p.add_argument('--env-file', type=Path, help='Optional local KEY=VALUE file; never included in reports')
    p.add_argument('--model', default=None, help='Defaults to CCSWITCH_MODEL or gpt-5.6-sol')
    a=p.parse_args()
    if a.output.exists(): p.error('Output exists; choose a new report filename')
    if a.env_file:
        allowed = {'CCSWITCH_API_KEY', 'CCSWITCH_BASE_URL', 'CCSWITCH_MODEL'}
        for line in a.env_file.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if not line or line.startswith('#'): continue
            key, sep, value = line.partition('=')
            if not sep or key.strip() not in allowed:
                p.error('Environment file must contain only CCSWITCH settings')
            os.environ[key.strip()] = value.strip().strip('"').strip("'")
    provider=OpenAICompatibleProvider(model=a.model or os.getenv('CCSWITCH_MODEL') or 'gpt-5.6-sol', max_retries=0)
    report=evaluate_agent(a.manifest, provider, max_attempts=a.max_attempts, total_timeout=a.total_timeout, max_output_tokens=a.max_output_tokens)
    report['requested_model']=provider.model
    report['provider_base_url']=provider.base_url
    report['max_output_tokens']=a.max_output_tokens
    report['implementation_sha256'] = {name: hashlib.sha256((ROOT/'src/webextractor'/name).read_bytes()).hexdigest() for name in ('agent_evaluation.py', 'rule_agent.py', 'agent_rules.py', 'openai_provider.py', 'extractor.py', 'content_blocks.py')}
    report['usage_total'] = {key: sum(attempt['usage'][key] for attempt in report['trace']['attempts'] if attempt.get('usage')) for key in ('input_tokens', 'output_tokens', 'total_tokens')} if all(attempt.get('usage') for attempt in report['trace']['attempts']) and report['trace']['attempts'] else None
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    summary={'output':str(a.output),'status':report['trace']['status'],'runtime_accepted':report['trace']['runtime_accepted'],'quality_evaluated':report['quality_evaluated'],'requested_model':provider.model,'cases':[{ 'id':x['id'], 'status':x['metrics']['status'], 'precision':x['metrics']['block_text_precision'], 'recall':x['metrics']['block_text_recall'], 'blocks_exact':x['metrics']['blocks_exact']} for x in report['cases']]}
    summary['usage_total'] = report['usage_total']
    summary['attempts'] = len(report['trace']['attempts'])
    summary['elapsed_seconds'] = report['trace']['elapsed_seconds']
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if report['trace']['runtime_accepted'] else 2
if __name__=='__main__': raise SystemExit(main())


