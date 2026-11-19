import unittest

from lxml import html

from src.webextractor.content_blocks import ContentBlock, extract_blocks, render_blocks


class TableBlockTests(unittest.TestCase):
    def test_table_cells_form_one_block_without_repeating_nested_paragraphs(self):
        root = html.fromstring('''<main><p>开头</p><table>
          <thead><tr><th>字段</th><th>值</th></tr></thead>
          <tbody><tr><td><p>标签</p></td><td>内<strong>容</strong></td></tr></tbody>
        </table><p>结尾</p></main>''')
        blocks = extract_blocks(root)
        self.assertEqual([(block.kind, block.text) for block in blocks], [
            ('paragraph', '开头'),
            ('table', '字段 | 值\n标签 | 内容'),
            ('paragraph', '结尾'),
        ])

    def test_table_renders_as_separate_text_rows_instead_of_a_list(self):
        blocks = [ContentBlock('list_item', '前一项', list_type='ul'),
                  ContentBlock('table', '字段 | 值\n标签 | 内容'),
                  ContentBlock('list_item', '后一项', list_type='ul')]
        rendered = render_blocks(blocks)
        self.assertEqual(rendered,
                         '- 前一项\n\n```\n字段 | 值\n标签 | 内容\n```\n\n- 后一项')

    def test_table_without_headers_keeps_literal_pipes_and_backticks(self):
        root = html.fromstring('<main><table><tr><td>a|b</td><td>```</td></tr></table></main>')
        blocks = extract_blocks(root)
        self.assertEqual(render_blocks(blocks), '````\na|b | ```\n````')
        self.assertEqual(blocks[0].text, 'a|b | ```')


if __name__ == '__main__':
    unittest.main()
