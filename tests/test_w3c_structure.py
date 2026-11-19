import unittest

from pathlib import Path

from src.webextractor.extractor import extract_html


class W3CStructureTests(unittest.TestCase):
    snapshot = Path(__file__).parents[1] / "samples" / "w3c_accessibility_intro_zh.html"

    def test_initial_validation_structure_is_preserved(self):
        result = extract_html(self.snapshot.read_bytes())
        texts = [block.text for block in result.blocks]
        self.assertEqual(result.title, "Web无障碍简介")
        self.assertIn("总结", texts)
        self.assertIn("更多例子", texts)
        self.assertIn("开始行动的小贴士 (英文)", texts)
        self.assertNotIn("About this translation", texts)
        self.assertNotIn("翻译者： 冉若曦 , 金凯 . Web 无障碍倡议（WAI）感谢这些翻译者们，并欢迎其他的翻译。", texts)
        self.assertNotIn("帮助提升本页", texts)

