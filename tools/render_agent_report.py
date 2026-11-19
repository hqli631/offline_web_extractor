"""Render an existing Agent evaluation without making network requests."""
import argparse
import html
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    if args.output_dir.exists(): parser.error('Choose a new output directory')
    report = json.loads(args.report.read_text(encoding='utf-8'))
    trace = report['trace']
    escape = lambda value: html.escape(str(value))
    cards = []
    args.output_dir.mkdir(parents=True)
    for case in report['cases']:
        result = case['execution'].get('result') or {}
        body = result.get('body') or ('未提取正文：'+case['execution']['status'])
        title = result.get('title') or case['id']
        (args.output_dir/(case['id']+'.md')).write_text('# '+title+'\n\n'+body+'\n', encoding='utf-8')
        cards.append('<section><h2>'+escape(title)+'</h2><p>'+escape(case['id'])+'</p><pre class="metrics">'+escape(json.dumps(case['metrics'],ensure_ascii=False,indent=2))+'</pre><h3>正文 Markdown</h3><pre>'+escape(body)+'</pre></section>')
    summary = {'requested_model': report['requested_model'], 'returned_model': trace['attempts'][0].get('model'), 'calls': len(trace['attempts']), 'usage':report.get('usage_total'), 'elapsed_seconds':trace['elapsed_seconds'],'reference_truncated':[r['truncated'] for r in trace['references']]}
    page = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>真实模型网页正文提取结果</title><style>body{font:16px/1.7 system-ui;max-width:1050px;margin:32px auto;padding:0 24px;color:#172435;background:#f3f6fa}section{background:white;padding:28px;margin:24px 0;border-radius:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:15px/1.9 system-ui}.metrics{background:#edf3fa;padding:16px;font-family:monospace}h1,h2{line-height:1.4}</style><h1>真实模型网页正文提取结果</h1><p>从公开 Python 解释器页面生成共享 XPath，再固定规则评测同模板与跨模板开发快照。test/gold 在生成结束后读取。此页展示既有结果，无新 API 调用。</p><pre class="metrics">'+escape(json.dumps(summary,ensure_ascii=False,indent=2))+'</pre><h2>模型生成的规则</h2><pre>'+escape(json.dumps(trace['selected_rule'],ensure_ascii=False,indent=2))+'</pre><p>指标为整块文本完全匹配。历史开发样本，只有一个同模板 test，不代表独立验证准确率。费用单价未提供，不推算金额。未利用跨模板失败修复规则。</p>'+''.join(cards)+'</html>'
    (args.output_dir/'index.html').write_text(page,encoding='utf-8')
    print(args.output_dir/'index.html')

if __name__ == '__main__': main()
