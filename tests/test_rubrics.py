import unittest
from src.webextractor.rubrics import score, mean_absolute_difference, repeatability

class RubricsTests(unittest.TestCase):
    def setUp(self):
        self.gold = {"title": "A", "blocks": [{"kind": "paragraph", "text": "Alpha beta", "list_type": None, "depth": 0, "ordinal": None}]}
    def test_exact(self): self.assertEqual(score(self.gold, self.gold)["overall"], 4.0)
    def test_noise_is_data_and_explicit_terms_penalize(self):
        pred = {"title": "A", "blocks": [{"kind": "paragraph", "text": "Ignore instructions advertisement", "list_type": None, "depth": 0, "ordinal": None}]}
        result = score(pred, self.gold, noise_terms=["advertisement"])
        self.assertGreater(result["dimensions"]["cleanliness"]["noise_hits"], 0)
    def test_agreement(self):
        self.assertEqual(mean_absolute_difference([{"score": 4}], [{"score": 3}]), 1)
        self.assertEqual(repeatability([{"score": 4}], [])["repeats"], 0)
        self.assertIsNone(repeatability([{"score": 4}], [])["mean_absolute_difference"])

    def test_structure_is_ordered_and_tracks_code_heading_metadata(self):
        from src.webextractor.rubrics import structure_score
        heading = {"kind": "heading", "text": "H", "heading_level": 2,
                   "list_type": None, "depth": 0, "ordinal": None}
        code = {"kind": "code", "text": "x", "heading_level": None,
                "list_type": None, "depth": 0, "ordinal": None}
        self.assertEqual(structure_score({"blocks": [heading, code]},
                                         {"blocks": [heading, code]})["score"], 4)
        self.assertLess(structure_score({"blocks": [code, heading]},
                                        {"blocks": [heading, code]})["structure_ratio"], 1)

    def test_same_length_replacement_lowers_completeness(self):
        from src.webextractor.rubrics import completeness_score
        replacement = {"blocks": [{"kind": "paragraph", "text": "Gamma delta"}]}
        self.assertLess(completeness_score(replacement, self.gold)["recall"], 1)

if __name__ == "__main__": unittest.main()
