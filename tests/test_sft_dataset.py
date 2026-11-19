import json
from pathlib import Path
import tempfile
import unittest
from tools.build_sft_dataset import build_examples, write_dataset
ROOT=Path(__file__).resolve().parents[1]
class SFTDatasetTests(unittest.TestCase):
 def trace(self): return json.loads((ROOT/'outputs/agent_lab.replay.v1.json').read_text(encoding='utf-8'))
 def split(self): return {'reference':{'split':'train','template_id':'fixture-v1'},'class-drift':{'split':'train','template_id':'fixture-v1'}}
 def test_build(self):
  rows,meta=build_examples(self.trace(),self.split()); self.assertEqual(len(rows),1); self.assertEqual(rows[0]['outcome'],'accepted'); self.assertNotIn('expected',json.dumps(rows)); self.assertIn('rule_no_match',json.dumps(rows[0]['messages'])); self.assertNotIn('status',rows[0]['messages'][-1]['content']); self.assertEqual(rows[0]['messages'][-1]['role'],'assistant')
  diagnostics,_=build_examples(self.trace(),self.split(),include_failed=True); self.assertEqual(len(diagnostics),2)
 def test_reject(self):
  t=self.trace(); t['quality_evaluated']=True
  with self.assertRaises(ValueError): build_examples(t,self.split())
  t=self.trace(); t['expected']={};
  with self.assertRaises(ValueError): build_examples(t,self.split())
 def test_write(self):
  with tempfile.TemporaryDirectory() as x:
   d=Path(x); (d/'split.json').write_text(json.dumps({'protocol':'x','pages':[{'id':'reference','split':'train','template_id':'x'},{'id':'class-drift','split':'train','template_id':'x'}]}),encoding='utf8'); (d/'trace.json').write_text(json.dumps(self.trace()),encoding='utf8'); o,r=d/'o.jsonl',d/'r.json'; self.assertEqual(write_dataset(d/'trace.json',d/'split.json',o,r)['examples_written'],1)
   with self.assertRaises(FileExistsError): write_dataset(d/'trace.json',d/'split.json',o,r)
if __name__=='__main__': unittest.main()
