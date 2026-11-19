"""Bounded DashScope Qwen evaluation using the existing MVP protocol."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.webextractor.agent_evaluation import evaluate_agent
from src.webextractor.qwen_provider import QwenProvider

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--model', default='qwen3.8-27b')
    p.add_argument('--max-attempts', type=int, default=1)
    p.add_argument('--max-output-tokens', type=int, default=512)
    p.add_argument('--total-timeout', type=float, default=90)
    a = p.parse_args()
    if a.output.exists(): p.error('Output exists; choose a new filename')
    provider = QwenProvider(model=a.model, max_retries=0)
    report = evaluate_agent(a.manifest, provider, max_attempts=a.max_attempts, max_output_tokens=a.max_output_tokens, total_timeout=a.total_timeout)
    report.update(requested_model=provider.model, provider_endpoint=provider.endpoint)
    attempts = report['trace']['attempts']
    report['usage_total'] = {k: sum(x['usage'][k] for x in attempts) for k in ('input_tokens','output_tokens','total_tokens')} if attempts and all(x.get('usage') for x in attempts) else None
    report['implementation_sha256'] = {name: hashlib.sha256((ROOT/'src/webextractor'/name).read_bytes()).hexdigest() for name in ('qwen_provider.py','rule_agent.py','agent_rules.py','agent_evaluation.py','extractor.py','content_blocks.py')}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'output':str(a.output),'model':provider.model,'status':report['trace']['status'],'usage_total':report['usage_total'],'elapsed_seconds':report['trace']['elapsed_seconds'],'attempts':[{k:x.get(k) for k in ('model','finish_reason','error')} for x in attempts],'cases':[{'id':c['id'],**c['metrics']} for c in report['cases']]},ensure_ascii=False))
    return 0 if report['trace']['runtime_accepted'] else 2

if __name__ == '__main__': raise SystemExit(main())
