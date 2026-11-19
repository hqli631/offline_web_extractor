import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.webextractor.toy_rl import run_experiment
p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,required=True); p.add_argument('--seed',type=int,default=7)
a=p.parse_args()
if a.output.exists(): p.error('output exists')
a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(run_experiment(seed=a.seed),ensure_ascii=False,indent=2)+'\n',encoding='utf8'); print(a.output)
