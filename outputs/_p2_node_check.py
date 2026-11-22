import json, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from pathlib import Path
from src.webextractor.rubrics_judge import build_prompt
root = Path('samples')
man = json.loads((root/'p2_manifest.json').read_text(encoding='utf-8'))
mapping = json.loads(Path('outputs/human_review/p2.blind.v1/sealed_mapping.json').read_text(encoding='utf-8'))
rev = {v:k for k,v in mapping.items()}
print('code | nodes_identical_20k_vs_40k | html_in_packet?')
for mc in man['cases']:
    sb = (root/mc['source']).read_bytes()
    cand = json.loads((root/mc['candidate']).read_text(encoding='utf-8-sig'))
    pred = {'title': cand['title'], 'blocks': cand['blocks']}
    g = json.loads((root/mc['gold']).read_text(encoding='utf-8-sig'))
    gold = {'title': g['title'], 'blocks': g['blocks']}
    p20,_,_ = build_prompt(sb, pred, gold, max_source_chars=20000)
    p40,_,_ = build_prompt(sb, pred, gold, max_source_chars=40000)
    n20 = [(n['ref'],n['xpath'],n['text']) for n in p20['source']['nodes']]
    n40 = [(n['ref'],n['xpath'],n['text']) for n in p40['source']['nodes']]
    code = rev[mc['case_id']]
    pkt = Path(f'outputs/human_review/p2.blind.v1/packets/{code}.md').read_text(encoding='utf-8')
    has_html = 's:html' in pkt
    print(f'{code} | {n20==n40} | {has_html}')
# P1.5 config
fz = json.loads(Path('outputs/rubrics_judge.node3.freeze.v4.json').read_text(encoding='utf-8'))
print('\nfreeze v4 keys:', list(fz.keys()))
print(json.dumps({k:v for k,v in fz.items() if k in ('config','settings','config_signature','judge_version','model')}, ensure_ascii=False)[:800])
