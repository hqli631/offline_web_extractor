from dataclasses import asdict
import json
from pathlib import Path
import unittest

from lxml import html

from src.webextractor.extractor import extract_html, remove_noise


class BreadcrumbHeadingTests(unittest.TestCase):
    def test_breadcrumb_token_removal_keeps_ordinary_lists_and_similar_names(self):
        result = extract_html('''<article><h1>标题</h1>
          <ol class="compact breadcrumb"><li>首页导航</li></ol>
          <ol class="breadcrumb-note"><li>这是正文列表</li></ol>
          <ol><li>普通有序项</li></ol><p>正文。</p>
        </article>''')
        self.assertNotIn('首页导航', result.body)
        self.assertEqual([block.text for block in result.blocks],
                         ['这是正文列表', '普通有序项', '正文。'])
        self.assertEqual([block.list_type for block in result.blocks[:2]], ['ol', 'ol'])

    def test_removed_breadcrumb_keeps_following_tail_text(self):
        root = html.fromstring('<div>前<ol class="breadcrumb"><li>导航</li></ol>后</div>')
        clean = remove_noise(root)
        self.assertEqual(''.join(clean.itertext()), '前后')

    def test_h2_keeps_inline_title_text_and_order_but_drops_permalink(self):
        result = extract_html('''<article><h1>文章标题</h1><p>首段。</p>
          <h2>更多<strong>资料</strong><a class="headerlink extra" href="#more">¶</a></h2>
          <ul><li>参考一</li><li>参考二</li></ul><p>末段。</p>
        </article>''')
        self.assertEqual(result.title, '文章标题')
        self.assertEqual([(block.kind, block.text) for block in result.blocks], [
            ('paragraph', '首段。'), ('heading', '更多资料'),
            ('list_item', '参考一'), ('list_item', '参考二'), ('paragraph', '末段。'),
        ])
        self.assertEqual(result.body, '首段。\n\n## 更多资料\n\n- 参考一\n- 参考二\n\n末段。')
        self.assertNotIn('文章标题', result.body)
        self.assertNotIn('¶', result.body)

    def test_iana_snapshot_matches_independently_annotated_structure(self):
        samples = Path(__file__).resolve().parents[1] / 'samples'
        result = extract_html((samples / 'iana_example_domains.html').read_bytes())
        expected = json.loads((samples / 'iana_example_domains.expected.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(result.status, 'ok')
        self.assertEqual(result.title, expected['title'])
        self.assertEqual(result.paragraphs, expected['paragraphs'])
        self.assertEqual(result.to_dict()['blocks'], expected['blocks'])
        self.assertNotIn('Instructions and Guides', result.body)
        self.assertIn('## Further Reading', result.body)


if __name__ == '__main__':
    unittest.main()
