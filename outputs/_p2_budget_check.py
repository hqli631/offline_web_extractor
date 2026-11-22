import json, sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
from pathlib import Path
from src.webextractor.rubrics_judge import build_prompt
root = Path('samples')
man = json.loads((root/'p2_manifest.json').read_text(encoding='utf-8'))
tot_dev = tot_test = 0
for mc in man['cases']:
    sb = (root/mc['source']).read_bytes()
    cand = json.loads((root/mc['candidate']).read_text(encoding='utf-8-sig'))
    pred = {'title': cand['title'], 'blocks': cand['blocks']}
    g = json.loads((root/mc['gold']).read_text(encoding='utf-8-sig'))
    gold = {'title': g['title'], 'blocks': g['blocks']}
    _,_,m = build_prompt(sb, pred, gold, max_source_chars=20000)
    if mc['split']=='development': tot_dev += m['prompt_chars']
    else: tot_test += m['prompt_chars']
ratio = 531485/170160  # P1.5 observed chars per total token
new_chars = tot_dev+tot_test
new_tok = new_chars/ratio
cross_tok = 531485/ratio
print(f'new18 prompt_chars: dev6={tot_dev} test12={tot_test} total={new_chars}')
print(f'P1.5 ratio={ratio:.3f} chars/token')
print(f'est new18 tokens={new_tok:.0f}  cross12 tokens={cross_tok:.0f}  sum={new_tok+cross_tok:.0f}')
print(f'est total with 15% margin={1.15*(new_tok+cross_tok):.0f}')
# freeze v4 files: is judge_cache included?
fz4 = json.loads(Path('outputs/rubrics_judge.node3.freeze.v4.json').read_text(encoding='utf-8'))
cache_in_freeze = [k for k in fz4['files'] if 'cache' in k]
print('freeze v4 cache entries:', cache_in_freeze)
fz1 = json.loads(Path('outputs/rubrics_judge.node3.freeze.v1.json').read_text(encoding='utf-8')) if Path('outputs/rubrics_judge.node3.freeze.v1.json').exists() else None
print('freeze v1 exists:', fz1 is not None)
# cache key construction
src = Path('tools/run_rubrics_judge.py').read_text(encoding='utf-8')
i = src.find('def _cache_key')
print(src[i:i+700] if i>=0 else 'no _cache_key; search key')
