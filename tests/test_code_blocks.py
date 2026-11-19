"""Code text must retain whitespace and remain inert in rendered output."""

from pathlib import Path
import unittest

from lxml import html

from src.webextractor.extractor import extract_html


class CodeBlockTests(unittest.TestCase):
    def test_highlighted_code_retains_whitespace_and_does_not_capture_tail(self):
        source = ('<article><p>Before.</p><pre><span>if ready:</span>\n'
                  '<span>    run(1,  2)</span>\n\n\tfinish()  \n</pre>'
                  'outside-code<p>After.</p></article>')
        result = extract_html(source)
        self.assertEqual([block.kind for block in result.blocks], ['paragraph', 'code', 'paragraph'])
        code = result.blocks[1]
        self.assertEqual(code.text, 'if ready:\n    run(1,  2)\n\n\tfinish()  \n')
        self.assertNotIn('outside-code', code.text)
        self.assertEqual(result.body.count('run(1,  2)'), 1)
        self.assertIn('Before.\n\n```\n', result.body)
        self.assertIn('\n```\n\nAfter.', result.body)

    def test_code_without_final_newline_is_not_modified_in_block(self):
        result = extract_html('<article><pre>  x = 1</pre></article>')
        self.assertEqual(result.status, 'ok')
        self.assertEqual(result.blocks[0].kind, 'code')
        self.assertEqual(result.blocks[0].text, '  x = 1')
        self.assertEqual(result.body, '```\n  x = 1\n```')

    def test_fence_is_longer_than_any_run_of_backticks_in_code(self):
        code = 'print("```")\n# ```` remains literal\n'
        result = extract_html('<article><pre>' + code + '</pre></article>')
        self.assertEqual(result.blocks[0].text, code)
        rendered_lines = result.body.splitlines()
        fence = rendered_lines[0]
        self.assertRegex(fence, r'^`{5,}$')
        self.assertEqual(rendered_lines[-1], fence)
        self.assertIn('# ```` remains literal', result.body)

    def test_empty_or_whitespace_only_pre_does_not_create_a_code_block(self):
        result = extract_html('<article><pre><span></span></pre><pre> \n\t</pre><p>Body.</p></article>')
        self.assertEqual([(block.kind, block.text) for block in result.blocks], [('paragraph', 'Body.')])
        self.assertNotIn('```', result.body)

    def test_code_is_text_and_is_never_executed(self):
        code = 'raise RuntimeError("must stay inert")\n'
        result = extract_html('<article><pre>' + code + '</pre></article>')
        self.assertEqual(result.blocks[0].text, code)
        self.assertIn('raise RuntimeError', result.body)

    def test_saved_interpreter_page_keeps_all_six_pre_blocks(self):
        snapshot = Path(__file__).resolve().parents[1] / 'samples' / 'python_interpreter_zh.html'
        source = snapshot.read_bytes()
        # Independent reading of the raw DOM: not generated extractor output.
        tree = html.fromstring(source)
        original_codes = [''.join(node.itertext()) for node in tree.xpath("//div[@role='main']//pre")]
        result = extract_html(source, container_xpath="//div[@role='main']")
        predicted_codes = [block.text for block in result.blocks if block.kind == 'code']
        self.assertEqual(len(original_codes), 6)
        self.assertEqual(predicted_codes, original_codes)
        self.assertEqual(len(result.blocks), 32)
        self.assertIn('#!/usr/bin/env python3\n# -*- coding: cp1252 -*-\n', predicted_codes)
        self.assertEqual(sum(block.kind != 'code' for block in result.blocks), 26)


if __name__ == '__main__':
    unittest.main()
