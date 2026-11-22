import json, sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
for cid in ['cal-interpreter-instruction_interference','cal-nasa-instruction_interference','cal-w3ca11y-instruction_interference']:
    cand = json.loads(Path(f'samples/calibration/{cid}.candidate.json').read_text(encoding='utf-8-sig'))
    texts = [b.get('text','') for b in cand['blocks']]
    hits = [t[:80] for t in texts if ('忽略' in t or '所有维度' in t or '4分' in t or 'ignore' in t.lower())]
    lab = json.loads(Path(f'samples/calibration/labels/{cid}.label.json').read_text(encoding='utf-8'))
    mut = lab.get('mutation',{})
    print(cid, '| candidate_injection_text_hits:', len(hits), '| mutation:', json.dumps(mut, ensure_ascii=False)[:150])
    for h in hits[:2]: print('   ', h)
