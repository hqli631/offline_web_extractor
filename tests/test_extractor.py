import unittest

from src.webextractor.extractor import extract_html


HTML = """
<main>
  <article class="post">
    <h1>标题</h1>
    <div class="content article-body">
      <p>第一段<strong>重点</strong>。</p>
      <div class="ad"><p>广告不应出现</p></div>
      <p>第二段。</p>
    </div>
  </article>
  <div class="related"><p>推荐阅读</p></div>
</main>
"""


class ExtractorTests(unittest.TestCase):
    def test_extracts_nested_text_and_removes_noise(self):
        result = extract_html(HTML)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.title, "标题")
        self.assertEqual(result.paragraphs, ["第一段重点。", "第二段。"])
        self.assertNotIn("广告", result.body)
        self.assertNotIn("推荐", result.body)

    def test_reports_no_candidate(self):
        result = extract_html("<html><body><p>孤立文本</p></body></html>")
        self.assertEqual(result.status, "no_candidate")


if __name__ == "__main__":
    unittest.main()
