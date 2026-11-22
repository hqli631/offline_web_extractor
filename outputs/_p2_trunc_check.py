import json, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from pathlib import Path
from src.webextractor.rubrics_judge import build_prompt
root = Path('samples')
man = json.loads((root/'p2_manifest.json').read_text(encoding='utf-8'))
mapping = json.loads(Path('outputs/human_review/p2.blind.v1/sealed_mapping.json').read_text(encoding='utf-8'))
rev = {v:k for k,v in mapping.items()}
print('code | case_id | split | raw_html_chars | trunc@20k(human) | trunc@40k(judge) | nodes@20k | nodes@40k | prompt_chars@40k')
for mc in man['cases']:
    sb = (root/mc['source']).read_bytes()
    cand = json.loads((root/mc['candidate']).read_text(encoding='utf-8-sig'))
    pred = {'title': cand['title'], 'blocks': cand['blocks']}
    gold = None
    if mc.get('gold'):
        g = json.loads((root/mc['gold']).read_text(encoding='utf-8-sig'))
        gold = {'title': g['title'], 'blocks': g['blocks']}
    from lxml import html
    tree = html.document_fromstring(sb, parser=html.HTMLParser(no_network=True))
    rawlen = len(html.tostring(tree, encoding='unicode'))
    _,_,m20 = build_prompt(sb, pred, gold, max_source_chars=20000)
    _,_,m40 = build_prompt(sb, pred, gold, max_source_chars=40000)
    code = rev[mc['case_id']]
    print(f"{code} | {mc['case_id']} | {mc['split']} | {rawlen} | {m20['source_truncated']} | {m40['source_truncated']} | {m20['source_nodes']} | {m40['source_nodes']} | {m40['prompt_chars']}")
