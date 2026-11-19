import json
import multiprocessing
import unittest

from src.webextractor.agent_rules import execute_rule, validate_rule


def rule(xpath='//article', exclusions=None):
    return dict(version=1, container_xpath=xpath, exclude_xpaths=exclusions or [])


class AgentRuleTests(unittest.TestCase):
    def test_strict_schema_and_duplicate_keys(self):
        valid = rule()
        self.assertEqual(validate_rule(json.dumps(valid)), valid)
        invalid = [dict(valid, version=True), dict(valid, code='print(1)'),
                   dict(valid, exclude_xpaths='//p'), dict(valid, container_xpath=''),
                   dict(valid, exclude_xpaths=['x']*33), [],
                   '{"version":1,"version":1,"container_xpath":"//p","exclude_xpaths":[]}']
        for candidate in invalid:
            with self.subTest(candidate=candidate):
                self.assertEqual(execute_rule('<p>x</p>', candidate)['status'], 'invalid_rule')

    def test_unique_match_exclusions_preserve_tail_and_identity(self):
        source = '<main><article><h1>Title</h1><p>First <span class="ad">AD</span> retained.</p><div class="extra"><p>Noise</p></div><p>Last</p></article><article><p>Wrong</p></article></main>'
        result = execute_rule(source, rule('//article[.//div[@class="extra"]]', ['.//span', './/div', './/div/p']))
        self.assertEqual(result['status'], 'ok', result)
        self.assertEqual(result['result']['title'], 'Title')
        self.assertEqual(result['result']['paragraphs'], ['First retained.', 'Last'])
        self.assertEqual(result['excluded_count'], 2)
        self.assertNotIn('Wrong', result['result']['body'])

    def test_zero_multiple_invalid_and_scalar_matches(self):
        source = '<article><p>x</p></article><article><p>y</p></article>'
        cases = [('//absent', 'rule_no_match', 0), ('//article', 'rule_ambiguous', 2),
                 ('//*[', 'invalid_xpath', None), ('count(//article)', 'non_element_xpath', None),
                 ('//p/text()', 'non_element_xpath', None)]
        for xpath, status, count in cases:
            with self.subTest(xpath=xpath):
                result = execute_rule(source, rule(xpath))
                self.assertEqual(result['status'], status, result)
                self.assertEqual(result['match_count'], count)
                self.assertIsNone(result['result'])

    def test_unicode_survives_reparse_without_charset_declaration(self):
        response = execute_rule('<article><h1>正文标题</h1><p>保留中文与缩进。</p></article>', rule())
        self.assertEqual(response['status'], 'ok', response)
        self.assertEqual(response['result']['title'], '正文标题')
        self.assertEqual(response['result']['paragraphs'], ['保留中文与缩进。'])

    def test_exclusions_are_validated_by_node_identity(self):
        source = '<main><article><p>Inside</p></article><p>Outside</p></main>'
        cases = [('.', 'exclusion_outside_container'), ('..', 'exclusion_outside_container'),
                 ('//p', 'exclusion_outside_container'), ('.//p/text()', 'non_element_xpath'),
                 ('true()', 'non_element_xpath'), ('//*[', 'invalid_xpath')]
        for xpath, status in cases:
            with self.subTest(xpath=xpath):
                result = execute_rule(source, rule(exclusions=[xpath]))
                self.assertEqual(result['status'], status, result)
                self.assertIsNone(result['result'])
        # A leading // is not inherently unsafe when all selected nodes are local.
        result = execute_rule('<article><p>Keep</p><div>Drop</div></article>', rule(exclusions=['//div']))
        self.assertEqual(result['status'], 'ok', result)

    def test_timeout_kills_worker_and_invalid_limits_fail_early(self):
        before = {child.pid for child in multiprocessing.active_children()}
        response = execute_rule('<article><p>x</p></article>', rule(), timeout_seconds=0.000001)
        self.assertEqual(response['status'], 'timeout', response)
        self.assertEqual({child.pid for child in multiprocessing.active_children()}, before)
        for value in [0, -1, float('nan'), True]:
            with self.assertRaises(ValueError):
                execute_rule('', rule(), timeout_seconds=value)


if __name__ == '__main__':
    unittest.main()
