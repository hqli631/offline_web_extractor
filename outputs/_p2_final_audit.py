import json, sys, hashlib, subprocess
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
fz4 = json.loads(Path('outputs/rubrics_judge.node3.freeze.v4.json').read_text(encoding='utf-8'))
judge_rel = 'src/webextractor/rubrics_judge.py'
frozen_judge = fz4['files'].get(judge_rel)
cur = sha(judge_rel)
print('judge code sha == freeze v4 record:', cur == frozen_judge, cur[:12])
b = json.loads(Path('outputs/p2.judge.v2.json').read_text(encoding='utf-8'))
c = json.loads(Path('outputs/p2.cross.v2.json').read_text(encoding='utf-8'))
vs = {(r['report']['judge_version'], r['report']['rubrics_version']) for r in b['cases']}
vc = {(r['report']['judge_version'], r['report']['rubrics_version']) for r in c['cases']}
print('p2 batch versions:', vs, '| cross versions:', vc)
print('p2 signature:', b['signature'])
print('cross signature:', c['signature'])
print('p2 splits:', {s: sum(1 for r in b['cases'] if r['split']==s) for s in ('development','frozen_test')})
print('cross splits:', {s: sum(1 for r in c['cases'] if r['split']==s) for s in ('development','frozen_test')})
print('all accepted p2:', all(r['report']['status']=='accepted' for r in b['cases']), '| cross:', all(r['report']['status']=='accepted' for r in c['cases']))
g = subprocess.run(['git','status','-sb'],capture_output=True,text=True).stdout.splitlines()[0]
print('git:', g)
print('usage p2 total:', b['usage_total_all_cases'], '| cross total:', c['usage_total_all_cases'])
