"""Provider selection is explicit and does not need network requests in tests."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from src.webextractor import agent_cli

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'samples/agent_lab/references.json'


class AgentCliTests(unittest.TestCase):
    def invoke(self, *arguments):
        with patch('sys.argv', ['agent', str(MANIFEST), *map(str, arguments)]), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return agent_cli.main()

    def test_qwen_uses_requested_default_and_preserves_model_trace(self):
        provider = Mock(model='qwen3.8-27b')
        trace = {'status': 'runtime_accepted', 'runtime_accepted': True,
                 'quality_evaluated': False, 'attempts': []}
        with tempfile.TemporaryDirectory() as folder, \
             patch('src.webextractor.qwen_provider.QwenProvider', return_value=provider) as constructor, \
             patch.object(agent_cli, 'run_agent', return_value=trace) as run, \
             patch.object(agent_cli, 'save_trace'):
            self.assertEqual(self.invoke('--provider', 'qwen', '--output', Path(folder)/'trace.json'), 0)
            constructor.assert_called_once_with(model='qwen3.8-27b', max_retries=0)
            self.assertIs(run.call_args.args[1], provider)
            self.assertEqual(trace['requested_model'], 'qwen3.8-27b')
            self.assertIn('qwen_provider.py', trace['implementation_sha256'])

    def test_qwen_and_ccswitch_accept_explicit_model(self):
        for kind, module in [('qwen', 'qwen_provider.QwenProvider'), ('ccswitch', 'openai_provider.OpenAICompatibleProvider')]:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as folder, \
                 patch('src.webextractor.'+module, return_value=Mock(model='explicit-model')) as constructor, \
                 patch.object(agent_cli, 'run_agent', return_value={'status': 'runtime_accepted', 'runtime_accepted': True, 'quality_evaluated': False, 'attempts': []}), \
                 patch.object(agent_cli, 'save_trace'):
                self.invoke('--provider', kind, '--model', 'explicit-model', '--output', Path(folder)/'trace.json')
                constructor.assert_called_once_with(model='explicit-model', max_retries=0)

    def test_network_provider_rejects_replay_and_replay_rejects_model(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'trace.json'
            for arguments in [('--provider', 'qwen', '--replay', 'fixture.json'),
                              ('--provider', 'replay', '--model', 'qwen3.8-27b')]:
                with self.subTest(arguments=arguments), self.assertRaises(SystemExit) as error:
                    self.invoke(*arguments, '--output', output)
                self.assertEqual(error.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
