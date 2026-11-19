"""Actual local DOM execution for a tiny finite rule-search RL experiment."""
from __future__ import annotations
from collections import Counter
import hashlib, math, random
from .agent_rules import execute_rule

DEFAULT_HTML = '''<html><body><article id="post"><h1>Offline extraction</h1><div class="content"><p>Introduction</p><p>Main result</p></div><nav><a>Navigation</a></nav><div class="promo"><p>Recommended</p></div><div class="discussion"><p>Comments</p></div></article></body></html>'''
GOLD = ("Introduction", "Main result")
NOISE_EXCLUSIONS = (".//nav", ".//*[contains(concat(' ', normalize-space(@class), ' '), ' promo ')]", ".//*[contains(concat(' ', normalize-space(@class), ' '), ' discussion ')]")

def _blocks(result):
    return tuple(str(b.get('text','')) for b in (result or {}).get('blocks',[]) if b.get('text'))

def metrics(predicted, gold):
    p,g=Counter(predicted),Counter(gold); hit=sum((p&g).values())
    precision=hit/len(predicted) if predicted else 0.0; recall=hit/len(gold) if gold else 1.0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
    return dict(precision=precision,recall=recall,f1=f1,exact=tuple(predicted)==tuple(gold))

class DOMRuleEnv:
    def __init__(self, source=DEFAULT_HTML, gold=GOLD):
        self.source=source; self._gold=tuple(gold); self.candidates={'content':"//article[@id='post']/div[@class='content']",'article':"//article[@id='post']",'partial':"//article[@id='post']/div[@class='content']/p[1]",'missing':"//article[@id='missing']"}; self._cache={}; self.phase='container'; self.container=None
    def reset(self): self.phase='container'; self.container=None; return {'phase':'container','actions':tuple(self.candidates)}
    def _run(self,name,exclusions):
        key=(name,tuple(exclusions))
        if key not in self._cache: self._cache[key]=execute_rule(self.source,{'version':1,'container_xpath':self.candidates[name],'exclude_xpaths':list(exclusions)},timeout_seconds=3.0)
        return self._cache[key]
    def step(self, action):
        if self.phase=='done': raise RuntimeError('Episode is finished; call reset()')
        if self.phase=='container':
            if action not in self.candidates: raise ValueError('Unknown container action: '+str(action))
            self.container=action; self.phase='cleanup'; return {'phase':'cleanup','actions':('stop','remove-noise')},0.0,False,{'container':action}
        if action not in ('stop','remove-noise'): raise ValueError('Unknown cleanup action: '+str(action))
        exclusions=NOISE_EXCLUSIONS if action=='remove-noise' else (); result=self._run(self.container,exclusions); self.phase='done'
        return {'phase':'done','status':result.get('status'),'match_count':result.get('match_count'),'block_count':len(_blocks(result.get('result')))},0.0,True,{'container':self.container,'cleanup':action,'result':result,'cache_key':(self.container,tuple(exclusions))}
    def evaluate(self, info, reward='corrected'):
        m=metrics(_blocks((info.get('result') or {}).get('result')),self._gold)
        if reward=='sparse': value=float(m['exact'])
        elif reward=='proxy': value=len(_blocks((info.get('result') or {}).get('result')))/max(1,len(self._gold))
        elif reward=='corrected': value=.30*m['precision']+.60*m['recall']+.10*float(m['exact'])
        else: raise ValueError('Unknown reward: '+str(reward))
        return dict(reward=value,**m,predicted_blocks=_blocks((info.get('result') or {}).get('result')),status=(info.get('result') or {}).get('status'))

def run_episode(env, first, second, reward):
    env.reset(); env.step(first); _,_,done,info=env.step(second); assert done
    m=env.evaluate(info,reward); return {'first':first,'second':second,'done':done,'metrics':m,'execution':{'status':info['result'].get('status'),'match_count':info['result'].get('match_count'),'cache_key':info['cache_key']}}

def _softmax(xs):
    m=max(xs); ws=[math.exp(x-m) for x in xs]; total=sum(ws); return [x/total for x in ws]
def _sample(ps,rng):
    x=rng.random(); total=0
    for i,p in enumerate(ps):
        total+=p
        if x<=total:return i
    return len(ps)-1
def _update(ls,i,a,ps,rate):
    for j in range(len(ls)): ls[j]+=rate*a*((1.0 if j==i else 0)-ps[j])

def train(env,reward,algorithm='reinforce',seed=7,episodes=240,group_size=4):
    if algorithm not in ('reinforce','grpo-like'): raise ValueError('unknown algorithm')
    rng=random.Random(seed); first=[0.0]*len(env.candidates); second=[0.0,0.0]; history=[]; count=episodes if algorithm=='reinforce' else max(20,episodes//3)
    for ep in range(count):
        fp,sp=_softmax(first),_softmax(second); samples=[]
        for _ in range(1 if algorithm=='reinforce' else group_size):
            fi,si=_sample(fp,rng),_sample(sp,rng); item=run_episode(env,tuple(env.candidates)[fi],('stop','remove-noise')[si],reward); samples.append((fi,si,item['metrics']['reward']))
        if algorithm=='grpo-like':
            avg=sum(x[2] for x in samples)/len(samples); scale=math.sqrt(sum((x[2]-avg)**2 for x in samples)/len(samples))+1e-8; samples=[(i,j,(v-avg)/scale) for i,j,v in samples]
        for i,j,a in samples: _update(first,i,a,fp,.25/(group_size if algorithm=='grpo-like' else 1)); _update(second,j,a,sp,.25/(group_size if algorithm=='grpo-like' else 1))
        if ep<3 or ep==count-1: history.append({'episode':ep+1,'samples':samples})
    fp,sp=_softmax(first),_softmax(second); fi=max(range(len(fp)),key=fp.__getitem__); si=max(range(len(sp)),key=sp.__getitem__); greedy=run_episode(env,tuple(env.candidates)[fi],('stop','remove-noise')[si],reward)
    return dict(algorithm=algorithm,reward=reward,seed=seed,episodes=episodes,greedy=greedy,first_probabilities=dict(zip(env.candidates,fp)),second_probabilities=dict(zip(('stop','remove-noise'),sp)),history=history,cache_entries=len(env._cache))

def run_experiment(source=DEFAULT_HTML,seed=7,episodes=240):
    runs=[train(DOMRuleEnv(source),reward,algorithm,seed=seed,episodes=episodes) for algorithm in ('reinforce','grpo-like') for reward in ('sparse','proxy','corrected')]
    raw=source.encode() if isinstance(source,str) else source
    return {'protocol':'actual local DOM XPath execution; two-step finite environment','seed':seed,'runs':runs,'source_sha256':hashlib.sha256(raw).hexdigest(),'note':'Toy evidence only; gold is reward-side state and never an observation; not industrial PPO/GRPO.'}
