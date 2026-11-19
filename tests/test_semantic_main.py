from pathlib import Path
import unittest

from lxml import html

from src.webextractor.extractor import extract_html, normalize_title


class SemanticMainTests(unittest.TestCase):
    def test_semantic_main_container_is_found_without_manual_xpath(self):
        source = '''
        <html><body>
          <div role="navigation"><p>导航文字</p></div>
          <div role="main">
            <h1>文档标题</h1><p>首段正文。</p><p>末段正文。</p>
          </div>
          <aside><p>侧栏文字</p></aside>
        </body></html>
        '''
        result = extract_html(source)
        self.assertEqual(result.status, 'ok')
        self.assertEqual(result.title, '文档标题')
        self.assertEqual(result.paragraphs, ['首段正文。', '末段正文。'])

    def test_main_element_and_role_do_not_duplicate_candidate(self):
        result = extract_html('<main role="main"><h1>T</h1><p>正文</p></main>')
        self.assertEqual(result.status, 'ok')
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.paragraphs, ['正文'])

    def test_headerlink_is_removed_but_other_title_text_is_preserved(self):
        source = '''
        <article><h1>认识¶符号：<a href="/reference">参考</a>
          <a class="extra headerlink" href="#title">¶</a>补充
        </h1><p>正文中的¶也应保留。</p></article>
        '''
        result = extract_html(source)
        self.assertEqual(result.title, '认识¶符号：参考 补充')
        self.assertEqual(result.body, '正文中的¶也应保留。')

    def test_title_normalization_does_not_mutate_original_node(self):
        heading = html.fromstring('<h1>标题<a class="headerlink">¶</a>尾文</h1>')
        original = html.tostring(heading)
        self.assertEqual(normalize_title(heading), '标题尾文')
        self.assertEqual(html.tostring(heading), original)

    def test_saved_chinese_document_keeps_all_paragraphs(self):
        snapshot = Path(__file__).resolve().parents[1] / 'samples' / 'python_appetite_zh.html'
        result = extract_html(snapshot.read_bytes())
        self.assertEqual(result.status, 'ok')
        self.assertEqual(result.title, '1. 课前甜点')
        self.assertEqual(len(result.paragraphs), 16)
        self.assertIn('高级数据类型允许在单一语句中表述复杂操作；', result.paragraphs)
        self.assertIn('使用缩进，而不是括号实现代码块分组；', result.paragraphs)
        self.assertIn('无需预声明变量或参数。', result.paragraphs)


if __name__ == '__main__':
    unittest.main()
