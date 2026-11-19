"""Offline tests for the Judge batch runner: cache-before-call, resume, budget."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from src.webextractor.rubrics_v2 import DIMENSIONS
from tools.run_rubrics_judge import load_manifest, run_batch, config_signature

SOURCE = '<html><head><meta charset="utf-8"></head><body><nav>Menu</nav><main><h1>1. Title</h1><p>Hello article</p></main></body></html>'
DOC = {"title": "1. Title", "blocks": [{"kind": "paragraph", "text": "Hello article"}]}


def assessment():
    return {"schema_version": 1, "dimensions": {name: {"score": 4, "status": "scored", "severity": "none",
            "reason": "Evidence matches", "evidence": [{"ref": "s:0", "quote": "1. Title"}]} for name in DIMENSIONS}}


class MockProvider:
    name = "mock-judge"
    model = "qwen3.8-27b"

    def __init__(self, value=None, fail=False):
        self.value = value if value is not None else assessment()
        self.fail = fail
        self.calls = 0

    def generate(self, prompt, **kwargs):
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider down")
        return {"content": deepcopy(self.value), "model": self.model, "finish_reason": "stop",
                "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}}


class ToolTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "page.html").write_text(SOURCE, encoding="utf-8")
        (self.root / "gold.json").write_text(json.dumps(DOC), encoding="utf-8")
        (self.root / "candidate.json").write_text(json.dumps(DOC), encoding="utf-8")
        noisy = {"title": "1. Title", "blocks": [{"kind": "paragraph", "text": "Hello article BUY NOW"}]}
        (self.root / "noisy.json").write_text(json.dumps(noisy), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def manifest(self, cases, name="manifest.json"):
        path = self.root / name
        path.write_text(json.dumps({"judge_manifest_version": 1, "cases": cases}), encoding="utf-8")
        return path

    def case(self, cid="c1", **overrides):
        base = {"case_id": cid, "template": "t", "split": "development", "source": "page.html",
                "candidate": "candidate.json", "gold": "gold.json"}
        base.update(overrides)
        return base

    def test_manifest_validation(self):
        with self.assertRaises(ValueError):
            load_manifest(self.manifest([self.case(), self.case()]))
        with self.assertRaises(ValueError):
            load_manifest(self.manifest([self.case(split="test")]))
        with self.assertRaises(ValueError):
            load_manifest(self.manifest([self.case(unknown_field=1)]))
        with self.assertRaises(ValueError):
            load_manifest(self.manifest([]))

    def test_batch_modes_usage_and_report(self):
        provider = MockProvider()
        path = self.manifest([self.case(), self.case("c2", gold=None, split="frozen_test")])
        report = run_batch(path, provider, max_calls=5, report_path=self.root / "report.json")
        self.assertEqual(provider.calls, 2)
        self.assertEqual([r["status"] for r in report["cases"]], ["accepted", "accepted"])
        self.assertEqual([r["case_meta"]["mode"] for r in report["cases"]], ["with_gold", "source_only"])
        self.assertEqual(report["usage_new_calls_only"]["total_tokens"], 60)
        saved = json.loads((self.root / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(len(saved["cases"]), 2)
        self.assertNotIn("Authorization", json.dumps(saved))
        self.assertEqual(report["cases"][1]["report"]["assessment"]["decision"], "uncertain")

    def test_cache_hit_costs_zero_calls(self):
        path = self.manifest([self.case(), self.case("c2", gold=None)])
        first = MockProvider()
        run_batch(path, first, max_calls=5)
        self.assertEqual(first.calls, 2)
        second = MockProvider()
        report = run_batch(path, second, max_calls=5)
        self.assertEqual(second.calls, 0)
        self.assertEqual(report["new_api_calls"], 0)
        self.assertEqual(report["cache_hits"], 2)
        self.assertTrue(all(r["cache_hit"] for r in report["cases"]))
        self.assertEqual(report["cases"][0]["report"]["assessment"],
                         run_batch(path, MockProvider(), max_calls=5)["cases"][0]["report"]["assessment"])

    def test_ignore_cache_forces_fresh_calls(self):
        path = self.manifest([self.case()])
        run_batch(path, MockProvider(), max_calls=5)
        provider = MockProvider()
        report = run_batch(path, provider, max_calls=5, ignore_cache=True)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(report["cache_hits"], 0)

    def test_budget_skip_then_resume(self):
        path = self.manifest([self.case(), self.case("c2", gold=None)])
        provider = MockProvider()
        partial = run_batch(path, provider, max_calls=1, report_path=self.root / "partial.json")
        self.assertEqual([r["status"] for r in partial["cases"]], ["accepted", "skipped_budget"])
        self.assertEqual(partial["skipped_budget"], 1)
        saved = json.loads((self.root / "partial.json").read_text(encoding="utf-8"))
        self.assertEqual(len(saved["cases"]), 2)
        resumed_provider = MockProvider()
        resumed = run_batch(path, resumed_provider, max_calls=5)
        self.assertEqual(resumed_provider.calls, 1)
        self.assertEqual([r["status"] for r in resumed["cases"]], ["accepted", "accepted"])
        self.assertTrue(resumed["cases"][0]["cache_hit"])
        self.assertFalse(resumed["cases"][1]["cache_hit"])

    def test_error_isolation_and_hash_guard(self):
        path = self.manifest([self.case(source_sha256="0" * 64), self.case("c2", gold=None)])
        provider = MockProvider()
        report = run_batch(path, provider, max_calls=5)
        self.assertEqual(report["cases"][0]["status"], "error")
        self.assertIn("SHA256", report["cases"][0]["error"]["detail"])
        self.assertEqual(report["cases"][1]["status"], "accepted")
        self.assertEqual(provider.calls, 1)

    def test_noise_terms_forwarded_to_program_score(self):
        path = self.manifest([self.case(candidate="noisy.json", noise_terms=["buy now"])])
        report = run_batch(path, MockProvider(), max_calls=5)
        program = report["cases"][0]["report"]["program_assessment"]
        self.assertEqual(program["dimensions"]["cleanliness"]["noise_hits"], {"buy now": 1})

    def test_rejected_response_cached_and_revalidated_without_call(self):
        bad = assessment()
        bad["schema_version"] = 2
        path = self.manifest([self.case()])
        first = MockProvider(value=bad)
        report = run_batch(path, first, max_calls=5)
        self.assertEqual(report["cases"][0]["status"], "error")
        self.assertEqual(first.calls, 1)
        second = MockProvider()
        replay = run_batch(path, second, max_calls=5)
        self.assertEqual(second.calls, 0)
        self.assertEqual(replay["cases"][0]["status"], "error")
        self.assertTrue(replay["cases"][0]["cache_hit"])

    def test_provider_failure_not_cached_and_retryable(self):
        path = self.manifest([self.case()])
        failing = MockProvider(fail=True)
        report = run_batch(path, failing, max_calls=5)
        self.assertEqual(report["cases"][0]["status"], "error")
        self.assertEqual(report["cases"][0]["report"]["error"]["stage"], "provider")
        healthy = MockProvider()
        retry = run_batch(path, healthy, max_calls=5)
        self.assertEqual(healthy.calls, 1)
        self.assertEqual(retry["cases"][0]["status"], "accepted")

    def test_gold_metadata_keys_projected_to_freeze_convention(self):
        from tools.run_rubrics_judge import run_case, config_signature
        from tools.build_calibration_set import sha256_json
        annotated = dict(DOC, annotation_note='meta', snapshot_sha256='x', paragraphs=['p'])
        (self.root / 'gold.json').write_text(json.dumps(annotated), encoding='utf-8')
        sig = config_signature('qwen3.8-27b', 2200, 20000, 90.0)
        provider = MockProvider()
        _key, report, meta, called = run_case(self.case(), self.root, provider, sig, {}, False, True)
        self.assertEqual(report['status'], 'accepted')
        self.assertEqual(meta['gold_sha256'], sha256_json(DOC))
        self.assertEqual(meta['candidate_sha256'], sha256_json(DOC))

    def test_build_provider_honors_batch_timeout(self):
        import os
        from unittest.mock import patch
        from tools.run_rubrics_judge import _build_provider
        with patch.dict(os.environ, {'QWEN_API_KEY': 'fake-test-key'}):
            provider = _build_provider('qwen3.8-27b', 90.0)
        self.assertEqual(provider.timeout_seconds, 90.0)
        self.assertEqual(provider.max_retries, 0)

    def test_signature_binds_versions_and_settings(self):
        sig = config_signature("qwen3.8-27b", 2200, 40000, 90.0)
        path = self.manifest([self.case()])
        run_batch(path, MockProvider(), max_calls=5)
        other = MockProvider()
        report = run_batch(path, other, max_calls=5, max_output_tokens=1024)
        self.assertEqual(other.calls, 1)
        self.assertEqual(report["cache_hits"], 0)
        self.assertEqual(report["signature"], config_signature("qwen3.8-27b", 1024, 40000, 90.0))
        self.assertNotEqual(sig, report["signature"])


if __name__ == "__main__":
    unittest.main()
