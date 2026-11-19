"""Offline transfer evaluation of an already recorded GPT rule; no API calls."""
from __future__ import annotations
import argparse
import hashlib
import html
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.webextractor.agent_evaluation import evaluate_fixed_rule
from src.webextractor.agent_rules import execute_rule

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error('Output directory exists; choose a new one')
    samples = ROOT / 'samples'
    manifest_path = samples / 'mvp_agent_manifest.v2.json'
    reference = samples / 'python_interpreter_zh.html'
    tests = [('same-template-appetite', 'python_appetite_zh.html', 'python_appetite_zh.expected.json'),
             ('cross-template-blurb', 'python_blurb.html', 'python_blurb.expected.json'),
             ('cross-template-iana', 'iana_example_domains.html', 'iana_example_domains.expected.json')]
    manifest = {'protocol': 'Development only. Reference interpreter is Sphinx; appetite tests same-template transfer. Blurb and IANA are cross-template stress cases. Historical gold; no independent validation claim. Test/gold are loaded after generation.',
                'references': [{'id': 'reference-interpreter', 'html': reference.name, 'sha256': digest(reference), 'split': 'reference'}],
                'tests': [{'id': name, 'html': source, 'sha256': digest(samples/source), 'split': 'test', 'expected': gold, 'expected_sha256': digest(samples/gold), 'expected_status': 'ok'} for name, source, gold in tests]}
    serialized = json.dumps(manifest, ensure_ascii=False, indent=2)+'\n'
    if manifest_path.exists() and manifest_path.read_text(encoding='utf-8') != serialized:
        raise ValueError('Existing manifest differs; preserve history and version it')
    if not manifest_path.exists(): manifest_path.write_text(serialized, encoding='utf-8')
    trace_path = ROOT/'outputs/agent.ccswitch.smoke.v2.json'
    trace = json.loads(trace_path.read_text(encoding='utf-8'))
    rule = trace['selected_rule']
    report = evaluate_fixed_rule(manifest_path, rule)
    report.update(method='saved-gpt-rule-offline-transfer', source_trace=str(trace_path.relative_to(ROOT)), source_trace_sha256=digest(trace_path),
                  requested_model=trace['requested_model'], returned_model=trace['attempts'][0]['model'],
                  new_api_calls=0, new_api_usage=None, source_generation_usage=trace['attempts'][0]['usage'],
                  note='Rule was generated on synthetic reference pages in smoke.v2. No new model generation on these real pages; this is post-hoc development transfer. Cross-template failures are expected boundaries, not same-template generalization estimates.')
    report['implementation_sha256'] = {name: digest(ROOT/'src/webextractor'/name) for name in ('agent_evaluation.py','agent_rules.py','extractor.py','content_blocks.py')}
    args.output_dir.mkdir(parents=True)
    cards = []
    for case, (_, filename, _) in zip(report['cases'], tests):
        baseline_rule = {'version': 1, 'container_xpath': ("//*[@role='main']" if 'appetite' in filename else "//article[contains(concat(' ',normalize-space(@class),' '),' text ')]" if 'blurb' in filename else "//div[contains(concat(' ',normalize-space(@class),' '),' help-article-flow ')]"), 'exclude_xpaths': []}
        baseline = execute_rule((samples/filename).read_bytes(), baseline_rule)
        from src.webextractor.agent_evaluation import score_execution
        gold = json.loads((samples/next(g for _, f, g in tests if f == filename)).read_text(encoding='utf-8'))
        case['handwritten_baseline'] = {'rule': baseline_rule, 'metrics': score_execution(baseline, gold)}
        result = case['execution'].get('result') or {}
        (args.output_dir/(case['id']+'.md')).write_text('# '+result.get('title','')+'\n\n'+result.get('body','[No body: '+case['execution']['status']+']')+'\n', encoding='utf-8')
        metrics = case['metrics']
        cards.append('<section><h2>'+html.escape(case['id'])+'</h2><p>'+html.escape(json.dumps(metrics,ensure_ascii=False))+'</p><div class="cols"><article><h3>GPT 规则结果</h3><pre>'+html.escape(result.get('body','无正文：'+case['execution']['status']))+'</pre></article><article><h3>冻结的开发集参考答案</h3><pre>'+html.escape('\n\n'.join(b['text'] for b in gold['blocks']))+'</pre></article></div></section>')
    (args.output_dir/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>GPT 正文提取效果</title><style>body{font:16px/1.65 system-ui;margin:32px;color:#172435;background:#f5f7fa}section{background:white;padding:24px;margin:24px 0;border-radius:12px}.cols{display:grid;grid-template-columns:1fr 1fr;gap:28px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:15px/1.8 system-ui}p{overflow-wrap:anywhere}h1,h2{line-height:1.3}@media(max-width:800px){.cols{grid-template-columns:1fr}}</style><h1>已保存 GPT 规则的真实网页迁移效果</h1><p>模型返回名：gpt-5.6-sol。规则来源为真实 API smoke 的合成参考页；本次仅在 CPU 上复用，无新增 API 调用。开发集整块文本匹配指标，不能代表独立验证或工业准确率。</p><pre>'+html.escape(json.dumps(rule,ensure_ascii=False,indent=2))+'</pre>'+''.join(cards)+'</html>'
    (args.output_dir/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps({'report':str(args.output_dir/'report.json'),'preview':str(args.output_dir/'index.html'),'cases':[{'id':c['id'],**c['metrics'],'handwritten':c['handwritten_baseline']['metrics']} for c in report['cases']]},ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
