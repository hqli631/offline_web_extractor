import unittest
from src.webextractor.toy_rl import *

class ToyRLTests(unittest.TestCase):
    def test_rewards_expose_hacking(self):
        env=RuleSearchEnv(); outcomes={c.name:assess(c) for c in env.candidates}
        self.assertGreater(proxy_reward(outcomes['long-noise']), proxy_reward(outcomes['exact']))
        self.assertGreater(corrected_reward(outcomes['exact']), corrected_reward(outcomes['long-noise']))
    def test_seeded_runs_reproduce_and_learn(self):
        a=train_reinforce(RuleSearchEnv(),'corrected',seed=3,episodes=250)
        b=train_reinforce(RuleSearchEnv(),'corrected',seed=3,episodes=250)
        self.assertEqual(a,b); self.assertEqual(a['greedy_action'],'exact')
    def test_grpo_group_relative_and_invalid(self):
        r=train_grpo(RuleSearchEnv(),'sparse',seed=2,updates=80,group_size=4)
        self.assertIn('advantages',r['history'][-1]); self.assertEqual(r['greedy_action'],'exact')
        with self.assertRaises(ValueError): train_grpo(RuleSearchEnv(),'sparse',group_size=1)
    def test_environment_is_finite(self):
        e=RuleSearchEnv(); e.reset(); e.step('exact')
        with self.assertRaises(RuntimeError): e.step('exact')

if __name__=='__main__': unittest.main()
