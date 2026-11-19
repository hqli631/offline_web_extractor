import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

from src.webextractor.rule_agent import ReplayProvider, run_agent, save_trace


ROOT = Path(__file__).resolve().parents[1]
RULE = dict(version=1, container_xpath="//div[@role='main']", exclude_xpaths=[])


class RuleAgentTests(unittest.TestCase):
    def references(self):
        return [dict(id=name, source=(ROOT / 'samples/drift_lab' / (name + '.html')).read_bytes())
                for name in ('reference', 'class-drift')]

    def test_authored_repair_runs_every_reference_and_preserves_trace(self):
        provider = ReplayProvider.from_file(ROOT / 'samples/agent_lab/replay.json')
        trace = run_agent(self.references(), provider, total_timeout=30)
        self.assertEqual(trace['status'], 'runtime_accepted', trace)
        self.assertEqual(len(trace['attempts']), 2)
        first, repaired = trace['attempts']
        self.assertEqual([row['status'] for row in first['feedback']], ['rule_no_match'] * 2)
        self.assertEqual([row['status'] for row in repaired['feedback']], ['ok'] * 2)
        self.assertEqual(repaired['prompt']['previous_attempts'][0]['pages'], first['feedback'])
        self.assertEqual(trace['selected_rule'], RULE)
        self.assertIsNone(trace['cost'])
        self.assertIsNone(repaired['usage'])
        self.assertFalse(trace['quality_evaluated'])
        self.assertNotIn('source', trace['references'][0])
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / 'trace.json'
            save_trace(trace, path)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['selected_rule'], RULE)
            with self.assertRaises(FileExistsError):
                save_trace(trace, path)

    def test_reference_interface_rejects_gold_or_test_fields(self):
        page = dict(self.references()[0], expected={'title': 'secret'})
        with self.assertRaises(ValueError):
            run_agent([page], ReplayProvider([RULE]))
        with self.assertRaises(ValueError):
            run_agent([self.references()[0]] * 2, ReplayProvider([RULE]))

    def test_exhaustion_is_explicit_and_invalid_schema_is_feedback(self):
        provider = ReplayProvider([dict(RULE, code='print(1)')])
        trace = run_agent(self.references(), provider, max_attempts=2)
        self.assertEqual(trace['status'], 'attempts_exhausted')
        self.assertFalse(trace['runtime_accepted'])
        self.assertIsNone(trace['selected_rule'])
        self.assertIn('Required keys', trace['attempts'][0]['error'])
        self.assertIn('Replay responses exhausted', trace['attempts'][1]['error'])
        self.assertEqual(trace['attempts'][1]['prompt']['previous_attempts'][0]['error'],
                         trace['attempts'][0]['error'])

    def test_response_and_token_budgets_prevent_execution(self):
        class ExcessUsage:
            def generate(self, prompt, **kwargs):
                return dict(content=RULE, usage=dict(output_tokens=100))
        with patch('src.webextractor.rule_agent.execute_rule') as execute:
            trace = run_agent(self.references(), ExcessUsage(), max_output_tokens=10)
            self.assertEqual(trace['status'], 'output_token_limit')
            execute.assert_not_called()
            trace = run_agent(self.references(), ReplayProvider(['x' * 100]),
                              max_response_chars=20, max_attempts=1)
            self.assertEqual(trace['status'], 'attempts_exhausted')
            self.assertTrue(trace['attempts'][0]['response']['omitted'])
            execute.assert_not_called()

    def test_openai_provider_metadata_is_accepted_and_traced(self):
        class Provider:
            name = 'test-openai'
            def generate(self, prompt, **kwargs):
                return dict(content=RULE, usage=dict(input_tokens=1, output_tokens=2, total_tokens=3), model='gpt-returned', finish_reason='stop')
        trace = run_agent(self.references(), Provider(), max_attempts=1, total_timeout=30)
        self.assertEqual(trace['status'], 'runtime_accepted')
        self.assertEqual(trace['attempts'][0]['model'], 'gpt-returned')
        self.assertEqual(trace['attempts'][0]['finish_reason'], 'stop')
        self.assertEqual(trace['attempts'][0]['usage']['total_tokens'], 3)
    def test_provider_elapsed_budget_is_checked_before_execution(self):
        class SlowProvider:
            def generate(self, prompt, **kwargs):
                time.sleep(.02)
                return dict(content=RULE)
        with patch('src.webextractor.rule_agent.execute_rule') as execute:
            trace = run_agent(self.references(), SlowProvider(), total_timeout=.001)
            self.assertEqual(trace['status'], 'total_timeout')
            execute.assert_not_called()

    def test_limits_reject_nonfinite_and_wrong_types(self):
        for kwargs in (dict(max_attempts=True), dict(total_timeout=float('inf')),
                       dict(execution_timeout=0), dict(max_attempts=11), dict(evidence_chars=-1)):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                run_agent(self.references(), ReplayProvider([RULE]), **kwargs)

    def test_all_reference_pages_must_succeed_and_evidence_is_bounded(self):
        responses = [dict(status='ok', result=dict(blocks=[dict(text='x')], body='x')),
                     dict(status='empty_body', result=dict(blocks=[], body=''))]
        with patch('src.webextractor.rule_agent.execute_rule', side_effect=responses) as execute:
            trace = run_agent(self.references(), ReplayProvider([RULE]), max_attempts=1, evidence_chars=10)
        self.assertEqual(execute.call_count, 2)
        self.assertEqual(trace['status'], 'attempts_exhausted')
        self.assertEqual(len(trace['references'][0]['html']), 10)
        self.assertTrue(trace['references'][0]['truncated'])
        self.assertEqual(trace['attempts'][0]['prompt']['reference_pages'], trace['references'])


if __name__ == '__main__':
    unittest.main()

