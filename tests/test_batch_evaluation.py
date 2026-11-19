import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.webextractor.batch_evaluate import run_batch
from src.webextractor.evaluate import evaluate


def paragraph_block(text):
    return {
        'kind': 'paragraph', 'text': text, 'list_type': None,
        'depth': 0, 'ordinal': None,
    }


class BatchEvaluationTests(unittest.TestCase):
    def write_json(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def make_case_files(self, directory, name='sample', source=None, expected=None):
        html_path = directory / (name + '.html')
        expected_path = directory / (name + '.expected.json')
        html_path.write_text(
            '<meta charset="utf-8">' + (source or '<article><h1>标题</h1><p>正文</p></article>'), encoding='utf-8',
        )
        self.write_json(expected_path, expected or {
            'title': '标题', 'paragraphs': ['正文'],
            'blocks': [paragraph_block('正文')],
        })
        return html_path, expected_path

    def manifest_case(self, case_id, html_path, expected_path, split, source_kind):
        return {
            'id': case_id, 'split': split, 'source_kind': source_kind,
            'html': html_path.name, 'expected': expected_path.name,
            'sha256': hashlib.sha256(html_path.read_bytes()).hexdigest(),
        }

    def test_batch_resolves_manifest_paths_and_isolates_missing_and_changed_snapshots(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / 'dataset'
            directory.mkdir()
            html_path, expected_path = self.make_case_files(directory)
            cases = [
                self.manifest_case('dev-real', html_path, expected_path, 'development', 'real'),
                self.manifest_case('validation-real', html_path, expected_path, 'validation', 'real'),
                self.manifest_case('dev-synthetic', html_path, expected_path, 'development', 'synthetic'),
            ]
            missing = self.manifest_case(
                'missing', html_path, expected_path, 'validation', 'real',
            )
            missing['html'] = 'does-not-exist.html'
            changed = self.manifest_case(
                'changed', html_path, expected_path, 'validation', 'real',
            )
            changed['sha256'] = '0' * 64
            cases.extend([missing, changed])
            manifest = directory / 'manifest.json'
            self.write_json(manifest, {'cases': cases})

            # The process cwd is outside the temporary dataset: all input paths
            # must be based on the manifest location, not on the shell cwd.
            report = run_batch(manifest)
            rows = {row['id']: row for row in report['cases']}
            self.assertEqual(len(rows), 5)
            for case_id in ('dev-real', 'validation-real', 'dev-synthetic'):
                self.assertEqual(rows[case_id]['outcome'], 'evaluated')
                self.assertTrue(rows[case_id]['metrics']['title_exact'])
                self.assertTrue(rows[case_id]['metrics']['blocks_exact'])
            for case_id in ('missing', 'changed'):
                self.assertEqual(rows[case_id]['outcome'], 'error')
                self.assertTrue(rows[case_id]['error'])
                self.assertFalse(rows[case_id].get('metrics'))

            groups = {(group['split'], group['source_kind']): group
                      for group in report['summary']}
            self.assertEqual(set(groups), {
                ('development', 'real'), ('development', 'synthetic'), ('validation', 'real'),
            })
            validation = groups[('validation', 'real')]
            self.assertEqual(validation['total'], 3)
            self.assertEqual(validation['evaluated'], 1)
            self.assertEqual(validation['errors'], 2)
            self.assertEqual(validation['structure_scored'], 1)
            self.assertEqual(validation['title_exact_rate'], 1.0)
            self.assertEqual(validation['blocks_exact_rate'], 1.0)

    def test_repeated_predicted_blocks_cannot_inflate_recall(self):
        with TemporaryDirectory() as temporary:
            html_path, expected_path = self.make_case_files(
                Path(temporary), source='<article><h1>标题</h1><p>正文</p><p>正文</p></article>',
            )
            metrics = evaluate(html_path, expected_path)
            self.assertEqual(metrics['block_text_precision'], 0.5)
            self.assertEqual(metrics['block_text_recall'], 1.0)
            self.assertFalse(metrics['blocks_exact'])

    def test_extra_list_text_is_noise_even_when_legacy_paragraphs_match(self):
        with TemporaryDirectory() as temporary:
            html_path, expected_path = self.make_case_files(
                Path(temporary),
                source='<article><h1>标题</h1><p>正文</p><ul><li>噪声</li></ul></article>',
            )
            metrics = evaluate(html_path, expected_path)
            self.assertTrue(metrics['body_exact'])
            self.assertFalse(metrics['blocks_exact'])
            self.assertEqual(metrics['block_text_precision'], 0.5)
            self.assertEqual(metrics['block_text_recall'], 1.0)

    def test_absent_structure_annotation_is_not_scored_as_success(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            html_path, expected_path = self.make_case_files(
                directory, expected={'title': '标题', 'paragraphs': ['正文']},
            )
            metrics = evaluate(html_path, expected_path)
            self.assertIsNone(metrics['block_text_precision'])
            self.assertIsNone(metrics['block_text_recall'])
            manifest = directory / 'manifest.json'
            self.write_json(manifest, {'cases': [self.manifest_case(
                'unannotated', html_path, expected_path, 'development', 'real',
            )]})
            report = run_batch(manifest)
            group = report['summary'][0]
            self.assertEqual(group['structure_scored'], 0)
            self.assertIsNone(group['blocks_exact_rate'])


if __name__ == '__main__':
    unittest.main()
