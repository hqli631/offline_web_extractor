import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.webextractor.rule_reuse import run_reuse


class ReuseQualityTests(unittest.TestCase):
    def test_controlled_drift_distinguishes_applicability_and_completeness(self):
        root = Path(__file__).parents[1]
        config = root / 'samples/drift_lab/reuse.json'
        expected = json.loads(config.read_text(encoding='utf-8'))
        report = run_reuse(config)
        for target, actual in zip(expected['pages'], report['pages']):
            self.assertEqual(actual['status'], target['expected_status'])
            quality = actual['quality']
            self.assertEqual(quality['blocks_exact'] if quality else None,
                             target['expected_blocks_exact'])
        moved = next(p for p in report['pages'] if p['id'] == 'content-moved')
        self.assertEqual(moved['status'], 'ok')
        self.assertEqual(moved['match_count'], 1)
        self.assertAlmostEqual(moved['quality']['block_text_recall'], 2/3)
        self.assertEqual(len(moved['quality']['missing_text_blocks']), 1)

    def test_gold_hash_mismatch_is_not_scored_as_success(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = b'<div role="main"><p>Text</p></div>'
            (directory / 'page.html').write_bytes(source)
            (directory / 'gold.json').write_text('{}', encoding='utf-8')
            config = {'rule': {'container_xpath': '//div[@role="main"]'},
                      'pages': [{'id': 'page', 'role': 'transfer', 'html': 'page.html',
                                 'sha256': hashlib.sha256(source).hexdigest(),
                                 'expected': 'gold.json', 'expected_sha256': '0'*64}]}
            path = directory / 'config.json'
            path.write_text(json.dumps(config), encoding='utf-8')
            result = run_reuse(path)['pages'][0]
            self.assertEqual(result['status'], 'error')
            self.assertIn('Expected SHA256 mismatch', result['error'])
            self.assertIsNone(result['quality'])


if __name__ == '__main__':
    unittest.main()
