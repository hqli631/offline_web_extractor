"""Offline rubric diagnostics for a recorded Agent evaluation. No API calls."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.webextractor.agent_evaluation import load_manifest, _read_case
from src.webextractor.rubrics_v2 import score, VERSION

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evaluation',type=Path,required=True)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists(): p.error('Output exists; choose a new filename')
    evaluation=json.loads(a.evaluation.read_text(encoding='utf-8'))
    if evaluation['manifest_sha256'] != sha(a.manifest): raise ValueError('Evaluation manifest hash mismatch')
    root,_,_,cases=load_manifest(a.manifest)
    recorded={row['id']:row for row in evaluation['cases']}
    if set(recorded)!={c['id'] for c in cases}: raise ValueError('Recorded cases differ from manifest')
    rows=[]
    for case in cases:
        _,gold=_read_case(root,case,expected=True)
        candidate=recorded[case['id']]
        if candidate['sha256']!=case['sha256']: raise ValueError('Case hash mismatch')
        execution=candidate['execution']
        predicted=execution.get('result') or {'title':'','blocks':[]}
        rows.append({'id':case['id'],'html_sha256':case['sha256'],'gold_sha256':case['expected_sha256'],
                     'execution_status':execution['status'],'assessment':score(predicted,gold)})
    report={'rubrics_version':VERSION,'method':'offline-recorded-evaluation','evaluation_sha256':sha(a.evaluation),
            'manifest_sha256':sha(a.manifest),'implementation_sha256':sha(ROOT/'src/webextractor/rubrics_v2.py'),
            'cases':rows,'new_api_calls':0,'note':'Reference-based diagnostics; not a calibrated Qwen Judge or human label.'}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(a.output),'cases':[{'id':r['id'],'decision':r['assessment']['decision'],
        'scores':{k:v['score'] for k,v in r['assessment']['dimensions'].items()},
        'issue_codes':sorted({i['code'] for i in r['assessment']['issues']})} for r in rows]},ensure_ascii=False))

if __name__=='__main__': main()
