"""Regression checks for readable output in VS Code Markdown preview."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src.webextractor.extractor import extract_html


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class MarkdownOutputTests(unittest.TestCase):
    def test_adjacent_paragraphs_have_a_blank_line(self):
        result = extract_html('<article><p>第一段。</p><p>第二段。</p></article>')
        self.assertEqual(result.body, '第一段。\n\n第二段。')

    def test_list_is_separated_from_surrounding_paragraphs(self):
        result = extract_html('''<article>
          <p>列表之前。</p>
          <ul><li>第一项。</li><li>第二项。</li></ul>
          <p>列表之后。</p>
        </article>''')
        self.assertEqual(
            result.body,
            '列表之前。\n\n- 第一项。\n- 第二项。\n\n列表之后。',
        )
        self.assertEqual(len(result.blocks), 4)

    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, '-m', 'src.webextractor.cli', *map(str, arguments)],
            cwd=PROJECT_ROOT, capture_output=True, text=True, encoding='utf-8',
            check=False,
        )

    def test_markdown_title_is_a_heading_and_text_title_stays_plain(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / 'source.html'
            source.write_text(
                '<meta charset="utf-8"><article><h1>1. 课前甜点</h1>'
                '<p>第一段。</p><p>第二段。</p></article>', encoding='utf-8',
            )
            for suffix, expected_title in (('.md', '# 1. 课前甜点'), ('.txt', '1. 课前甜点')):
                with self.subTest(suffix=suffix):
                    output = folder / ('body' + suffix)
                    process = self.run_cli(source, '--text-output', output)
                    self.assertEqual(process.returncode, 0, process.stderr)
                    content = output.read_text(encoding='utf-8')
                    self.assertEqual(
                        content, expected_title + '\n\n第一段。\n\n第二段。\n',
                    )

    def test_missing_input_reports_usage_error_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / 'missing-practice.html'
            output = Path(directory) / 'should-not-exist.md'
            process = self.run_cli(missing, '--text-output', output)
            self.assertEqual(process.returncode, 2)
            self.assertIn('error:', process.stderr)
            self.assertIn('missing-practice.html', process.stderr)
            self.assertNotIn('Traceback', process.stderr)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
