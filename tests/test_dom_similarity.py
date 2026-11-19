from collections import Counter
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.webextractor.dom_similarity import (connected_components, multiset_jaccard,
                                             feature_settings, render_report, run_manifest,
                                             structural_features)


class DomSimilarityTests(unittest.TestCase):
    def test_text_attributes_urls_and_hidden_script_do_not_define_structure(self):
        first = '<main id="first"><h1>Title</h1><p class="lead"><a href="/a">Alpha</a></p></main>'
        second = '<main class="changed"><h1>Different</h1><p><a href="/b">Beta</a></p>' \
                 '<script>irrelevant()</script></main>'
        a, b = structural_features(first), structural_features(second)
        self.assertEqual(a, b)
        self.assertEqual(multiset_jaccard(a, b), 1.0)
        self.assertEqual(a['main/p/a'], 1)

    def test_same_prose_in_different_wrappers_has_lower_similarity(self):
        a = structural_features('<main><h1>Title</h1><p>Text</p></main>')
        b = structural_features('<main><div><h1>Title</h1><p>Text</p></div></main>')
        self.assertLess(multiset_jaccard(a, b), 1.0)
        self.assertGreater(multiset_jaccard(a, b), 0.0)

    def test_repeated_path_multiplicity_changes_score(self):
        a = structural_features('<main><p>One</p></main>')
        b = structural_features('<main><p>One</p><p>Two</p></main>')
        self.assertAlmostEqual(multiset_jaccard(a, b), 2/3)
        self.assertEqual(multiset_jaccard(Counter(), Counter()), 1.0)

    def test_presence_and_cap_remove_different_amounts_of_length_variation(self):
        short = '<main>' + '<p>Text</p>' * 2 + '</main>'
        long = '<main>' + '<p>Text</p>' * 20 + '</main>'
        self.assertEqual(structural_features(short), structural_features(short, 'full-counts'))
        self.assertEqual(multiset_jaccard(structural_features(short, 'full-presence'),
                                         structural_features(long, 'full-presence')), 1.0)
        capped = structural_features(long, 'full-capped')
        self.assertEqual(capped['main/p'], 3)
        self.assertEqual(capped['main'], 1)
        self.assertAlmostEqual(multiset_jaccard(structural_features(short, 'full-capped'),
                                               capped), 3 / 4)

    def test_suffix_mode_preserves_local_paths_beyond_outer_wrappers(self):
        original = '<main><article><section><p>Text</p></section></article></main>'
        wrapped = '<div>' + original + '</div>'
        full = multiset_jaccard(structural_features(original, 'full-presence'),
                                structural_features(wrapped, 'full-presence'))
        local_a = structural_features(original, 'suffix-presence')
        local_b = structural_features(wrapped, 'suffix-presence')
        self.assertIn('article/section/p', local_a)
        self.assertIn('article/section/p', local_b)
        self.assertGreater(multiset_jaccard(local_a, local_b), full)
        self.assertTrue(all(len(path.split('/')) <= 3 for path in local_b))

    def test_semantic_mode_reads_only_bounded_roles_and_keeps_tag_features(self):
        main = '<div role="main"><p class="a">Text</p></div>'
        nav = '<div role="navigation"><p id="b">Other</p></div>'
        self.assertEqual(structural_features(main), structural_features(nav))
        features = structural_features(main, 'semantic-presence')
        self.assertIn('div/p', features)
        self.assertIn('semantic:main:div/p', features)
        self.assertLess(multiset_jaccard(features, structural_features(nav, 'semantic-presence')), 1.0)
        unrelated = main.replace('class="a"', 'class="changed" data-note="navigation"')
        self.assertEqual(features, structural_features(unrelated, 'semantic-presence'))
        self.assertEqual(structural_features('<div role="unknown"><p>x</p></div>', 'semantic-presence'),
                         structural_features('<div><p>x</p></div>', 'semantic-presence'))

    def test_modes_validate_on_empty_source_and_expose_fixed_settings(self):
        with self.assertRaises(ValueError):
            structural_features('', 'unknown')
        self.assertEqual(feature_settings('full-capped')['count_cap'], 3)
        self.assertEqual(feature_settings('suffix-presence')['suffix_depth'], 3)
        repeated = '<main><div><p>x</p></div><div><p>x</p></div><div><p>x</p></div><div><p>x</p></div></main>'
        self.assertEqual(structural_features(repeated, 'suffix-capped')['main/div/p'], 3)
        self.assertEqual(feature_settings('suffix-capped')['count_cap'], 3)

    def test_connected_components_flag_transitive_false_similarity(self):
        scores = {('a', 'b'): 0.6, ('b', 'c'): 0.6, ('a', 'c'): 0.1}
        components, warnings = connected_components(['a', 'b', 'c'], scores, 0.5)
        self.assertEqual(components, [['a', 'b', 'c']])
        self.assertEqual(warnings[0]['below_threshold_pairs'],
                         [dict(left='a', right='c', score=0.1)])

    def test_manifest_reports_false_merges_and_input_errors(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            payload = b'<main><p>Text</p></main>'
            (directory / 'page.html').write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()
            pages = [dict(id=page_id, html='page.html', sha256=digest, manual_group=group,
                          source_kind='synthetic', split='development')
                     for page_id, group in [('a', 'one'), ('b', 'two')]]
            pages.append(dict(id='bad', html='page.html', sha256='0'*64,
                              manual_group='one', source_kind='real', split='development'))
            path = directory / 'manifest.json'
            path.write_text(json.dumps(dict(pages=pages)), encoding='utf-8')
            result = run_manifest(path, 0.9)
            self.assertEqual(len(result['false_merge_pairs']), 1)
            self.assertEqual(len(result['errors']), 1)
            self.assertEqual(result['errors'][0]['id'], 'bad')
            variant = run_manifest(path, 0.9, 'semantic-presence')
            self.assertEqual(variant['settings']['mode'], 'semantic-presence')
            self.assertIn('bounded explicit ARIA roles', variant['settings']['semantic_source'])
            rendered = render_report(variant)
            self.assertIn('semantic-presence', rendered)
            self.assertNotIn('不用正文、class、id或URL', rendered)

    def test_manifest_rejects_validation_and_invalid_threshold(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / 'manifest.json'
            path.write_text(json.dumps(dict(pages=[dict(id='validation', split='validation')])),
                            encoding='utf-8')
            result = run_manifest(path, 0.5)
            self.assertEqual(len(result['pages']), 0)
            self.assertIn('Only development', result['errors'][0]['error'])
            with self.assertRaises(ValueError):
                run_manifest(path, 1.1)

    def test_manual_same_template_can_be_split_by_wrapper_change(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            pages = []
            for page_id, markup in [('a', '<main><p>One</p></main>'),
                                    ('b', '<main><div><p>Two</p></div></main>')]:
                payload = markup.encode('utf-8')
                (directory / (page_id + '.html')).write_bytes(payload)
                pages.append(dict(id=page_id, html=page_id+'.html',
                                  sha256=hashlib.sha256(payload).hexdigest(),
                                  manual_group='same-reviewed-template',
                                  source_kind='synthetic', split='development'))
            path = directory / 'manifest.json'
            path.write_text(json.dumps(dict(pages=pages)), encoding='utf-8')
            result = run_manifest(path, 0.9)
            self.assertEqual(result['components'], [['a'], ['b']])
            self.assertEqual(len(result['false_split_pairs']), 1)


if __name__ == '__main__':
    unittest.main()
