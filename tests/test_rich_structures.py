import unittest

from lxml import html

from src.webextractor.content_blocks import extract_blocks, render_blocks


class RichStructureTests(unittest.TestCase):
    def blocks(self, markup):
        return extract_blocks(html.fromstring(markup))

    def test_quote_paragraphs_preserve_boundaries_and_do_not_duplicate_lists(self):
        blocks = self.blocks('<main><p>Outside</p><blockquote><p>First <em>quote</em>.</p>'
                             '<ul><li>Evidence</li></ul><p>Second quote.</p></blockquote></main>')
        self.assertEqual([(b.kind, b.text) for b in blocks], [
            ('paragraph', 'Outside'), ('quote', 'First quote.'),
            ('list_item', 'Evidence'), ('quote', 'Second quote.')])
        self.assertIn('> First quote.', render_blocks(blocks))
        self.assertEqual(render_blocks(blocks).count('Evidence'), 1)

    def test_definition_descriptions_preserve_paragraph_and_nested_list_order(self):
        blocks = self.blocks('<main><dl><dt>Term</dt><dd>Introduction<ul><li>One</li>'
                             '<li>Two</li></ul>After<p>Separate paragraph.</p></dd>'
                             '<dt>Next</dt><dd>Definition</dd></dl></main>')
        self.assertEqual([(b.kind, b.text) for b in blocks], [
            ('definition_term', 'Term'), ('definition_description', 'Introduction'),
            ('list_item', 'One'), ('list_item', 'Two'), ('definition_description', 'After'),
            ('definition_description', 'Separate paragraph.'), ('definition_term', 'Next'),
            ('definition_description', 'Definition')])
        self.assertNotIn('- Term', render_blocks(blocks))
        self.assertEqual(render_blocks(blocks).count('One'), 1)

    def test_list_note_is_identified_by_inbound_numbered_reference(self):
        blocks = self.blocks('<main><p>Claim<a id="ref-a" href="#note-arbitrary">[12]</a></p>'
                             '<ol><li id="note-arbitrary"><p>Note text.</p>'
                             '<a href="#ref-a">↩</a></li></ol></main>')
        self.assertEqual([b.kind for b in blocks], ['paragraph', 'footnote'])
        note = blocks[-1]
        self.assertEqual((note.text, note.footnote_label, note.source_id),
                         ('Note text.', '[12]', 'note-arbitrary'))
        self.assertNotIn('↩', render_blocks(blocks))

    def test_linked_list_item_with_non_note_label_stays_a_list_item(self):
        blocks = self.blocks('<main><p><a href="#topic">See topic</a></p>'
                             '<ol><li id="topic">Normal item</li><li>Second</li></ol></main>')
        self.assertEqual([b.kind for b in blocks], ['paragraph', 'list_item', 'list_item'])
        self.assertEqual([b.ordinal for b in blocks[1:]], [1, 2])

    def test_orphan_list_items_recover_text_without_repeating_paragraphs(self):
        blocks = self.blocks('<main><div><p>Features</p><li><p>One</p></li>'
                             '<li>Two<strong>!</strong></li></div></main>')
        self.assertEqual([(b.kind, b.text) for b in blocks], [
            ('paragraph', 'Features'), ('list_item', 'One'), ('list_item', 'Two!')])
        self.assertTrue(all(b.list_type == 'ul' for b in blocks[1:]))


if __name__ == '__main__':
    unittest.main()
