import unittest

from src.webextractor.extractor import extract_html


class ContainerSemanticsTests(unittest.TestCase):
    def test_ancestor_article_title_wins_over_first_body_section(self):
        result = extract_html('<article><h1>Actual title</h1><div class="entry-content">'
                              '<h2>First section</h2><p>Body</p></div></article>')
        self.assertEqual(result.title, 'Actual title')
        self.assertEqual([b.text for b in result.blocks], ['First section', 'Body'])

    def test_body_inside_header_does_not_duplicate_itself_as_lead(self):
        result = extract_html('<main><header><h1>Title</h1><div class="entry-content">'
                              '<p>Lead once.</p></div></header></main>')
        self.assertEqual(result.paragraphs, ['Lead once.'])

    def test_removed_ad_heading_cannot_shift_title_deletion(self):
        result = extract_html('<main><h2 class="ad">Advertisement</h2>'
                              '<h2>Real title</h2><p>Body</p></main>')
        self.assertEqual(result.title, 'Real title')
        self.assertEqual([b.text for b in result.blocks], ['Body'])

    def test_legacy_main_uses_local_h2_and_does_not_repeat_it(self):
        result = extract_html('<body><div id="banner"><h1>Site</h1></div>'
                              '<div id="main"><h2>Article</h2><p>Text</p>'
                              '<h3>Section</h3><p>Last</p></div></body>')
        self.assertEqual(result.title, 'Article')
        self.assertEqual([b.text for b in result.blocks], ['Text', 'Section', 'Last'])

    def test_later_h2_is_not_promoted_to_title(self):
        result = extract_html('<main><p>Opening</p><h2>Section</h2><p>Text</p></main>')
        self.assertEqual(result.title, '')
        self.assertIn('Section', result.body)

    def test_explicit_body_retains_header_lead_and_discards_outer_metadata(self):
        result = extract_html('<main><header><h1>Title</h1><p>Lead</p></header>'
                              '<p>Author metadata</p><section class="post__content">'
                              '<p>Body</p><p>Conclusion</p></section></main>')
        self.assertEqual(result.title, 'Title')
        self.assertEqual(result.paragraphs, ['Lead', 'Body', 'Conclusion'])

    def test_orphan_list_aside_is_content_but_complementary_and_toc_are_noise(self):
        result = extract_html('<article><h1>Title</h1><div class="toc"><ul><li>Index</li></ul></div>'
                              '<aside><p>Features</p><li>One</li></aside>'
                              '<aside role="complementary"><li>Sidebar</li></aside>'
                              '<p>End</p></article>')
        self.assertEqual([b.text for b in result.blocks], ['Features', 'One', 'End'])


if __name__ == '__main__':
    unittest.main()
