"""Heading hierarchy and semantic footnotes must survive正文提取."""

from pathlib import Path
import unittest

from src.webextractor.extractor import extract_html


class HeadingFootnoteTests(unittest.TestCase):
    def test_heading_levels_and_inline_text_keep_document_order(self):
        result = extract_html('''<article><h1>文章标题</h1>
          <h2>第二级<strong>标题</strong><a class="headerlink">¶</a></h2>
          <p>普通段落。</p>
          <h3>第三级<a class="headerlink extra">¶</a>补充</h3>
          <h4>第四级</h4><h5>第五级</h5><h6>第六级</h6>
        </article>''')
        headings = [block for block in result.blocks if block.kind == 'heading']
        self.assertEqual([block.heading_level for block in headings], [2, 3, 4, 5, 6])
        self.assertEqual([block.text for block in headings],
                         ['第二级标题', '第三级补充', '第四级', '第五级', '第六级'])
        self.assertEqual(result.body,
                         '## 第二级标题\n\n普通段落。\n\n### 第三级补充\n\n'
                         '#### 第四级\n\n##### 第五级\n\n###### 第六级')
        self.assertNotIn('文章标题', result.body)
        self.assertNotIn('¶', result.body)

    def test_semantic_footnote_wrapper_is_kept_without_duplicate_paragraph(self):
        result = extract_html('''<article><h1>标题</h1>
          <p>正文引用<a role="doc-noteref" href="#fn1">[1]</a>。</p>
          <aside class="footnote-list brackets">
            <aside class="footnote brackets" role="doc-footnote" id="fn1">
              <span class="label">[<a role="doc-backlink" href="#ref1">1</a>]</span>
              <p>脚注包含<strong>重要</strong>文字。</p>
            </aside>
          </aside>
          <aside><p>普通侧栏不属于正文。</p></aside>
        </article>''')
        self.assertEqual([block.kind for block in result.blocks], ['paragraph', 'footnote'])
        footnote = result.blocks[1]
        self.assertEqual(footnote.text, '脚注包含重要文字。')
        self.assertEqual(footnote.footnote_label, '[1]')
        self.assertEqual(footnote.source_id, 'fn1')
        self.assertEqual(result.body, '正文引用[1]。\n\n[1] 脚注包含重要文字。')
        self.assertEqual(result.body.count('脚注包含重要文字。'), 1)
        self.assertNotIn('普通侧栏', result.body)
        serialized = result.to_dict()['blocks']
        self.assertNotIn('heading_level', serialized[0])
        self.assertNotIn('footnote_label', serialized[0])
        self.assertEqual(serialized[1]['footnote_label'], '[1]')
        self.assertEqual(serialized[1]['source_id'], 'fn1')

    def test_role_and_class_token_are_semantic_signals_not_substrings(self):
        result = extract_html('''<article><h1>标题</h1>
          <aside role="doc-footnote" id="role-note"><span class="label">[a]</span><p>角色脚注。</p></aside>
          <aside class="extra footnote" id="class-note"><span class="label">[b]</span><p>类名脚注。</p></aside>
          <aside class="footnote-ad"><p>前缀相似广告。</p></aside>
          <aside class="ad">
            <aside class="footnote" id="inside-ad"><p>广告包装中的文字。</p></aside>
          </aside>
        </article>''')
        self.assertEqual([block.text for block in result.blocks], ['角色脚注。', '类名脚注。'])
        self.assertTrue(all(block.kind == 'footnote' for block in result.blocks))
        self.assertNotIn('前缀相似广告', result.body)
        self.assertNotIn('广告包装中的文字', result.body)

    def test_saved_interpreter_page_preserves_heading_hierarchy_and_footnote(self):
        snapshot = Path(__file__).resolve().parents[1] / 'samples' / 'python_interpreter_zh.html'
        result = extract_html(snapshot.read_bytes(), container_xpath="//div[@role='main']")
        self.assertEqual(result.status, 'ok')
        self.assertEqual(result.title, '2. 使用 Python 的解释器')
        self.assertEqual(len(result.blocks), 32)
        self.assertEqual(sum(block.kind == 'code' for block in result.blocks), 6)
        h3 = [block for block in result.blocks
              if block.kind == 'heading' and block.heading_level == 3]
        self.assertEqual([block.text for block in h3],
                         ['2.1.1. 传入参数', '2.1.2. 交互模式', '2.2.1. 源文件的字符编码'])
        footnotes = [block for block in result.blocks if block.kind == 'footnote']
        self.assertEqual(len(footnotes), 1)
        self.assertEqual(footnotes[0].footnote_label, '[1]')
        self.assertEqual(footnotes[0].source_id, 'id2')
        self.assertEqual(footnotes[0].text,
                         'Unix 系统中，为了不与同时安装的 Python 2.x 冲突，Python 3.x 解释器默认安装的执行文件名不是 python。')
        self.assertEqual(result.body.count(footnotes[0].text), 1)
        self.assertIn('这样，就可以在 shell 中运行 Python 了 [1]', result.body)
        self.assertNotIn('¶', result.body)
        self.assertNotIn('当前页', result.body)


if __name__ == '__main__':
    unittest.main()
