import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.webextractor.agent_evaluation import evaluate_agent, evaluate_fixed_rule, load_manifest, score_execution
from src.webextractor.rule_agent import ReplayProvider

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'samples/agent_lab/gate7_manifest.json'
RULE = {'version': 1, 'container_xpath': "//div[@role='main']", 'exclude_xpaths': []}


class AgentEvaluationTests(unittest.TestCase):
    def test_test_html_and_gold_are_read_only_after_generation_returns(self):
        manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
        test_paths = {(MANIFEST.parent / c[key]).resolve()
                      for c in manifest['tests'] for key in ('html', 'expected')}
        generated = False
        reads = []
        read_bytes, read_text = Path.read_bytes, Path.read_text

        def checked_bytes(path):
            if path.resolve() in test_paths:
                self.assertTrue(generated, 'Test/gold read before generation completed')
                reads.append(path.resolve())
            return read_bytes(path)

        def checked_text(path, *args, **kwargs):
            if path.resolve() in test_paths:
                self.assertTrue(generated, 'Test/gold read before generation completed')
                reads.append(path.resolve())
            return read_text(path, *args, **kwargs)

        def generated_trace(*args, **kwargs):
            nonlocal generated
            self.assertFalse(reads)
            generated = True
            return {'selected_rule': None, 'runtime_accepted': False}

        with patch.object(Path, 'read_bytes', checked_bytes), \
             patch.object(Path, 'read_text', checked_text), \
             patch('src.webextractor.agent_evaluation.run_agent', side_effect=generated_trace):
            evaluate_agent(MANIFEST, object())
        self.assertEqual(set(reads), test_paths)

    def test_manifest_rejects_cross_split_duplicate_paths_or_hashes(self):
        original = json.loads(MANIFEST.read_text(encoding='utf-8'))
        for duplicate in ('html', 'sha256'):
            with self.subTest(duplicate=duplicate), tempfile.TemporaryDirectory() as folder:
                manifest = json.loads(json.dumps(original))
                manifest['tests'][0][duplicate] = manifest['references'][0][duplicate]
                path = Path(folder) / 'manifest.json'
                path.write_text(json.dumps(manifest), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'disjoint'):
                    load_manifest(path)

    def test_structure_comparison_preserves_heading_and_footnote_fields(self):
        blocks = [{'kind': 'heading', 'text': 'Section', 'heading_level': 2},
                  {'kind': 'footnote', 'text': 'Note', 'footnote_label': '[1]', 'source_id': 'id2'}]
        actual = [dict(block, list_type=None, depth=0, ordinal=None) for block in blocks]
        execution = {'status': 'ok', 'result': {'blocks': actual}}
        self.assertTrue(score_execution(execution, {'blocks': blocks})['blocks_exact'])
        for field, value in (('heading_level', 3), ('footnote_label', '[2]'), ('source_id', 'id3')):
            with self.subTest(field=field):
                changed = json.loads(json.dumps(blocks))
                changed[0 if field == 'heading_level' else 1][field] = value
                self.assertFalse(score_execution(execution, {'blocks': changed})['blocks_exact'])

    def test_manifest_has_disjoint_reference_and_test_splits(self):
        _, _, refs, tests = load_manifest(MANIFEST)
        self.assertTrue({c['id'] for c in refs}.isdisjoint({c['id'] for c in tests}))

    def test_fixed_rule_scores_independent_test_pages(self):
        report = evaluate_fixed_rule(MANIFEST, RULE)
        self.assertEqual(report['reference_ids'], ['reference'])
        rows = {r['id']: r for r in report['cases']}
        self.assertTrue(rows['class-drift']['metrics']['blocks_exact'])
        self.assertFalse(rows['role-drift']['metrics']['status_match'])
        self.assertFalse(rows['duplicate-main']['metrics']['status_match'])
        self.assertLess(rows['content-moved']['metrics']['block_text_recall'], 1.0)

    def test_repair_agent_never_receives_test_pages_and_scores_after_trace(self):
        provider = ReplayProvider.from_file(ROOT / 'samples/agent_lab/replay.json')
        report = evaluate_agent(MANIFEST, provider, total_timeout=30)
        self.assertEqual(report['trace']['status'], 'runtime_accepted')
        self.assertEqual(report['trace']['references'][0]['id'], 'reference')
        prompt = json.dumps(report['trace'], ensure_ascii=False)
        self.assertNotIn('duplicate-main', prompt)
        rows = {r['id']: r for r in report['cases']}
        self.assertTrue(rows['class-drift']['metrics']['blocks_exact'])
        self.assertEqual(rows['duplicate-main']['execution']['status'], 'rule_ambiguous')
        self.assertLess(rows['content-moved']['metrics']['block_text_recall'], 1.0)

    def test_no_repair_is_explicitly_distinct(self):
        provider = ReplayProvider.from_file(ROOT / 'samples/agent_lab/replay.json')
        report = evaluate_agent(MANIFEST, provider, max_attempts=1, total_timeout=30)
        self.assertFalse(report['trace']['runtime_accepted'])
        self.assertTrue(all(r['execution']['status'] == 'agent_no_rule' for r in report['cases']))


if __name__ == '__main__':
    unittest.main()
