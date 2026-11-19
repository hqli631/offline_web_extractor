import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.webextractor.rule_reuse import run_reuse


class RuleReuseTests(unittest.TestCase):
    def make_page(self, directory, page_id, source, role='transfer'):
        path = directory / (page_id + '.html')
        path.write_text('<meta charset="utf-8">' + source, encoding='utf-8')
        return {
            'id': page_id, 'role': role, 'html': path.name,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    def make_config(self, directory, pages, xpath="//div[@role='main']"):
        path = directory / 'reuse.json'
        path.write_text(json.dumps({
            'rule': {'id': 'semantic-main', 'container_xpath': xpath, 'frozen_from': 'reference'},
            'pages': pages,
        }, ensure_ascii=False), encoding='utf-8')
        return path

    def test_frozen_rule_transfers_between_pages_with_different_text(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / 'snapshots'
            directory.mkdir()
            reference = self.make_page(
                directory, 'reference',
                '<nav><p>导航</p></nav><div role="main"><h1>第一篇</h1><p>甲页正文。</p></div>',
                role='reference',
            )
            transfer = self.make_page(
                directory, 'transfer',
                '<div role="main"><h1>第二篇</h1><p>乙页正文。</p><p>新增一段。</p></div><footer><p>页脚</p></footer>',
            )
            report = run_reuse(self.make_config(directory, [reference, transfer]))
            pages = {page['id']: page for page in report['pages']}
            for page in pages.values():
                self.assertEqual(page['status'], 'ok')
                self.assertEqual(page['match_count'], 1)
                self.assertIsNone(page.get('error'))
            self.assertEqual(pages['reference']['role'], 'reference')
            self.assertEqual(pages['transfer']['role'], 'transfer')
            self.assertEqual(pages['reference']['extraction']['paragraphs'], ['甲页正文。'])
            self.assertEqual(pages['transfer']['extraction']['title'], '第二篇')
            self.assertEqual(pages['transfer']['extraction']['paragraphs'], ['乙页正文。', '新增一段。'])

    def test_page_specific_rule_fails_without_automatic_fallback(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            reference = self.make_page(
                directory, 'reference', '<article id="first-story"><p>首篇。</p></article>', role='reference',
            )
            transfer = self.make_page(
                directory, 'transfer', '<article id="second-story"><p>次篇。</p></article>',
            )
            report = run_reuse(self.make_config(
                directory, [reference, transfer], xpath="//article[@id='first-story']",
            ))
            self.assertEqual(report['pages'][0]['status'], 'ok')
            failed = report['pages'][1]
            self.assertEqual(failed['status'], 'rule_no_match')
            self.assertEqual(failed['match_count'], 0)
            self.assertIsNone(failed['extraction'])

    def test_multiple_matches_are_reported_as_ambiguous(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            page = self.make_page(directory, 'ambiguous',
                                  '<div role="main"><p>甲。</p></div><div role="main"><p>乙。</p></div>')
            result = run_reuse(self.make_config(directory, [page]))['pages'][0]
            self.assertEqual(result['status'], 'rule_ambiguous')
            self.assertEqual(result['match_count'], 2)
            self.assertIsNone(result['extraction'])

    def test_changed_and_missing_snapshots_do_not_stop_other_pages(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            changed = self.make_page(directory, 'changed', '<div role="main"><p>旧文</p></div>')
            (directory / changed['html']).write_text('<meta charset="utf-8"><div role="main"><p>新文</p></div>', encoding='utf-8')
            missing = {'id': 'missing', 'role': 'transfer', 'html': 'absent.html', 'sha256': '0' * 64}
            good = self.make_page(directory, 'good', '<div role="main"><p>正文。</p></div>')
            report = run_reuse(self.make_config(directory, [changed, missing, good]))
            pages = {page['id']: page for page in report['pages']}
            for page_id in ('changed', 'missing'):
                self.assertEqual(pages[page_id]['status'], 'error')
                self.assertTrue(pages[page_id]['error'])
                self.assertIsNone(pages[page_id]['extraction'])
            self.assertEqual(pages['good']['status'], 'ok')
            self.assertEqual(pages['good']['extraction']['body'], '正文。')

    def test_scalar_and_text_xpath_are_rejected(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            page = self.make_page(directory, 'reference', '<div role="main"><p>正文。</p></div>', role='reference')
            for xpath in ('count(//p)', '//p/text()'):
                with self.subTest(xpath=xpath):
                    with self.assertRaises(ValueError):
                        run_reuse(self.make_config(directory, [page], xpath=xpath))


if __name__ == '__main__':
    unittest.main()
