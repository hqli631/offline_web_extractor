from pathlib import Path
import unittest

from src.webextractor.extractor import extract_html


class ContentBlockTests(unittest.TestCase):
    def test_paragraphs_and_list_items_keep_document_order_without_duplication(self):
        source = '''<article>
          <p>开头。</p>
          <ul><li><p>第一项<strong>重点</strong>。</p></li><li>第二项。</li></ul>
          <p>结尾。</p>
        </article>'''
        result = extract_html(source)
        self.assertEqual(result.status, 'ok')
        self.assertEqual(
            [(block.kind, block.text) for block in result.blocks],
            [('paragraph', '开头。'), ('list_item', '第一项重点。'),
             ('list_item', '第二项。'), ('paragraph', '结尾。')],
        )
        self.assertEqual(result.body, '开头。\n\n- 第一项重点。\n- 第二项。\n\n结尾。')
        # The legacy p-only field remains unchanged for previous evaluations.
        self.assertEqual(result.paragraphs, ['开头。', '第一项重点。', '结尾。'])

    def test_list_with_no_p_is_still_nonempty_content(self):
        result = extract_html('<article><ul><li>甲<a href="/b">乙</a>丙</li></ul></article>')
        self.assertEqual(result.status, 'ok')
        self.assertEqual(result.paragraphs, [])
        self.assertEqual(result.body, '- 甲乙丙')
        self.assertEqual(result.blocks[0].kind, 'list_item')
        self.assertEqual(result.blocks[0].list_type, 'ul')
        self.assertEqual(result.blocks[0].depth, 0)

    def test_ordered_list_honors_start_and_item_value(self):
        result = extract_html('''<article><ol start="3">
          <li>第三项</li><li value="7">第七项</li><li>第八项</li>
        </ol></article>''')
        self.assertEqual(result.body, '3. 第三项\n7. 第七项\n8. 第八项')
        self.assertEqual([block.ordinal for block in result.blocks], [3, 7, 8])
        self.assertTrue(all(block.list_type == 'ol' for block in result.blocks))

    def test_nested_list_does_not_duplicate_descendant_text_or_reorder_tail(self):
        result = extract_html('''<article><ul>
          <li>父项<ul><li>子项<strong>重点</strong></li></ul>父项尾文</li>
          <li>下一项</li>
        </ul></article>''')
        self.assertEqual(
            [(block.kind, block.text, block.depth) for block in result.blocks],
            [('list_item', '父项', 0), ('list_item', '子项重点', 1),
             ('list_item_continuation', '父项尾文', 0), ('list_item', '下一项', 0)],
        )
        self.assertEqual(result.body, '- 父项\n  - 子项重点\n  父项尾文\n- 下一项')

    def test_p_after_nested_list_stays_in_its_parent_item(self):
        result = extract_html('''<article><ul><li>
          <p>父项首段</p><ul><li>子项</li></ul><p>父项续段</p>
        </li></ul></article>''')
        self.assertEqual(
            [(block.kind, block.text) for block in result.blocks],
            [('list_item', '父项首段'), ('list_item', '子项'),
             ('list_item_continuation', '父项续段')],
        )
        self.assertEqual(result.body.count('子项'), 1)
        self.assertEqual(result.paragraphs, ['父项首段', '父项续段'])

    def test_json_preserves_block_metadata(self):
        result = extract_html('<article><ul><li>条目</li></ul></article>').to_dict()
        self.assertEqual(result['blocks'][0]['kind'], 'list_item')
        self.assertEqual(result['blocks'][0]['text'], '条目')
        self.assertEqual(result['blocks'][0]['list_type'], 'ul')
        self.assertEqual(result['blocks'][0]['depth'], 0)

    def test_saved_chinese_document_has_three_list_items_in_original_order(self):
        snapshot = Path(__file__).resolve().parents[1] / 'samples' / 'python_appetite_zh.html'
        result = extract_html(snapshot.read_bytes())
        self.assertEqual(result.title, '1. 课前甜点')
        self.assertEqual(len(result.blocks), 16)
        self.assertEqual(len(result.paragraphs), 16)
        self.assertEqual([block.text for block in result.blocks], result.paragraphs)
        items = [block for block in result.blocks if block.kind == 'list_item']
        self.assertEqual([block.text for block in items], [
            '高级数据类型允许在单一语句中表述复杂操作；',
            '使用缩进，而不是括号实现代码块分组；',
            '无需预声明变量或参数。',
        ])
        for item in items:
            self.assertIn('- ' + item.text, result.body)
            self.assertEqual(result.body.count(item.text), 1)


if __name__ == '__main__':
    unittest.main()
