import unittest
from src.webextractor.dom_rl import DOMRuleEnv, run_episode, run_experiment

class DOMRLTests(unittest.TestCase):
    def test_two_step_actual_execution(self):
        env=DOMRuleEnv(); self.assertEqual(env.reset()['phase'],'container'); _,_,done,_=env.step('article'); self.assertFalse(done); _,_,done,info=env.step('remove-noise'); self.assertTrue(done); self.assertIn(info['result']['status'],('ok','empty_body')); self.assertGreaterEqual(info['result'].get('match_count',0),1)
    def test_reward_hacking_and_correction(self):
        env=DOMRuleEnv(); broad_proxy=run_episode(env,'article','stop','proxy'); exact=run_episode(env,'content','stop','corrected'); broad_corrected=run_episode(env,'article','stop','corrected'); cleaned=run_episode(env,'article','remove-noise','corrected'); self.assertGreater(broad_proxy['metrics']['reward'],exact['metrics']['reward']); self.assertGreater(cleaned['metrics']['reward'],broad_corrected['metrics']['reward'])
    def test_invalid_actions(self):
        env=DOMRuleEnv(); env.reset()
        with self.assertRaises(ValueError): env.step('bad')
    def test_seeded_experiment(self):
        a=run_experiment(episodes=20); b=run_experiment(episodes=20); self.assertEqual(a,b); self.assertEqual(len(a['runs']),6); self.assertTrue(all('execution' in r['greedy'] for r in a['runs']))

if __name__=='__main__': unittest.main()

