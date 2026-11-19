import unittest

from lxml import html

from src.webextractor.extractor import candidate_score, extract_html
from src.webextractor.evaluate import _char_precision, _char_recall


class BoundaryTests(unittest.TestCase):
    def test_removed_ad_keeps_following_text(self):
        result = extract_html('<article><p>前<span class="ad">广告</span>后</p></article>')
        self.assertEqual(result.body, '前后')

    def test_ad_substring_is_not_noise_token(self):
        a = html.fromstring('<article class="reading"><p>正文</p></article>')
        b = html.fromstring('<article><p>正文</p></article>')
        self.assertEqual(candidate_score(a), candidate_score(b))

    def test_non_paragraph_article_has_explicit_status(self):
        result = extract_html('<article><h1>标题</h1><div>正文没有p</div></article>')
        self.assertEqual(result.status, 'empty_body')

    def test_empty_input(self):
        self.assertEqual(extract_html('  ').status, 'empty_input')

    def test_character_counts_respect_multiplicity(self):
        self.assertEqual(_char_precision('aaaa', 'abcd'), 0.25)
        self.assertEqual(_char_recall('aaaa', 'abcd'), 0.25)

    def test_manual_xpath_can_select_unrecognized_layout(self):
        source = '<div id="story"><p>正文</p></div>'
        self.assertEqual(extract_html(source).status, 'no_candidate')
        self.assertEqual(extract_html(source, container_xpath="//div[@id='story']").body, '正文')

    def test_xpath_must_select_elements(self):
        with self.assertRaises(ValueError):
            extract_html('<p>正文</p>', container_xpath='//p/text()')
