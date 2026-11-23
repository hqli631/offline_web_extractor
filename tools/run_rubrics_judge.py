"""Bounded real DashScope Qwen Judge batch runner with cache and resume.

Cases come from a manifest. The cache key binds judge/rubrics versions, model,
budget settings and the exact prompt hash, so a cached response is only reused
for an identical request. The cache is checked BEFORE any provider call and is
written after every case; the report is also written incrementally. Resume an
interrupted batch by rerunning the same manifest with a NEW output filename:
cached cases cost zero new API calls. No API key is written to report/cache.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.webextractor.extractor import extract_html
from src.webextractor.rubrics_judge import JUDGE_VERSION, build_prompt, run_judge
from src.webextractor.rubrics_v2 import VERSION as RUBRICS_VERSION
from src.webextractor import rubrics_judge as _v12_module


def _judge_module(judge_version: str):
    """Opt-in judge protocol selector. Default 1.2 keeps byte-frozen behavior;
    1.4 wraps v1.2 with adjudicated protocol anchors (rubrics_judge_v14)."""
    if judge_version == "1.2":
        return _v12_module
    if judge_version == "1.4":
        from src.webextractor import rubrics_judge_v14 as m
        return m
    raise ValueError("Unsupported judge version: " + judge_version)

SPLITS = ("smoke", "development", "frozen_test")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(value) -> str:
    return sha256_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def load_manifest(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != {"judge_manifest_version", "cases"}:
        raise ValueError("Manifest needs judge_manifest_version and cases")
    if raw["judge_manifest_version"] != 1:
        raise ValueError("Unsupported judge_manifest_version")
    cases = raw["cases"]
    if not isinstance(cases, list) or not cases:
        raise ValueError("Manifest cases must be a nonempty list")
    seen = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Each case must be an object")
        allowed = {"case_id", "template", "split", "source", "candidate", "gold", "noise_terms", "source_sha256"}
        if not set(case) <= allowed:
            raise ValueError(f"Unknown case fields: {sorted(set(case) - allowed)}")
        for key in ("case_id", "template", "split", "source"):
            if not isinstance(case.get(key), str) or not case.get(key):
                raise ValueError(f"Case {key} must be a nonempty string")
        if case["case_id"] in seen:
            raise ValueError(f"Duplicate case_id {case['case_id']}")
        seen.add(case["case_id"])
        if case["split"] not in SPLITS:
            raise ValueError(f"Invalid split {case['split']}")
        if case.get("gold") is not None and not isinstance(case["gold"], str):
            raise ValueError("gold must be null or a path")
        candidate = case.get("candidate", "extract")
        if candidate != "extract" and not (isinstance(candidate, str) and candidate):
            raise ValueError("candidate must be 'extract' or a path")
        if case.get("noise_terms") is not None and (
                not isinstance(case["noise_terms"], list)
                or any(not isinstance(t, str) or not t.strip() for t in case["noise_terms"])):
            raise ValueError("noise_terms must contain nonempty strings")
        if case.get("source_sha256") is not None and not isinstance(case["source_sha256"], str):
            raise ValueError("source_sha256 must be a hex string when present")
    return raw


def _read_doc(path: Path, name: str) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict) or not isinstance(doc.get("blocks"), list) or "title" not in doc:
        raise ValueError(f"{name} must contain title and blocks")
    return doc


def _candidate_for(case: dict, root: Path, source_bytes: bytes) -> tuple[dict, str]:
    spec = case.get("candidate", "extract")
    if spec == "extract":
        result = extract_html(source_bytes)
        return {"title": result.title, "blocks": result.to_dict()["blocks"]}, "extractor"
    candidate = _read_doc(root / spec, "candidate")
    return {"title": candidate["title"], "blocks": candidate["blocks"]}, "file"


def config_signature(model: str, max_output_tokens: int, max_source_chars: int, timeout_seconds: float,
                     judge_version: str = JUDGE_VERSION) -> dict:
    return {"model": model, "max_output_tokens": max_output_tokens,
            "max_source_chars": max_source_chars, "timeout_seconds": timeout_seconds,
            "judge_version": judge_version, "rubrics_version": RUBRICS_VERSION}


def cache_key(signature: dict, prompt_sha256: str) -> str:
    return sha256_json({"signature": signature, "prompt_sha256": prompt_sha256})


def run_case(case: dict, root: Path, provider, signature: dict, cache: dict,
             ignore_cache: bool, allow_call: bool, probe: dict | None = None,
             judge_module=None):
    """Return (key, report_or_None, case_meta, made_api_call). Cache is checked first."""
    jm = judge_module if judge_module is not None else _v12_module
    source_bytes = (root / case["source"]).read_bytes()
    recorded = case.get("source_sha256")
    actual = sha256_bytes(source_bytes)
    if recorded is not None and recorded.lower() != actual:
        raise ValueError("Source SHA256 mismatch; snapshot changed after manifest freeze")
    predicted, origin = _candidate_for(case, root, source_bytes)
    gold = None
    if case.get("gold"):
        gdoc = _read_doc(root / case["gold"], "gold")
        # Project to the document schema used by the node-3 freeze builder so
        # case_meta.gold_sha256 matches the frozen convention. Annotation files
        # may carry extra metadata keys; build_prompt only uses title/blocks,
        # so the prompt and cache key are unaffected by this projection.
        gold = {"title": gdoc["title"], "blocks": gdoc["blocks"]}
    noise_terms = case.get("noise_terms") or ()
    prompt, _registry, metadata = jm.build_prompt(source_bytes, predicted, gold,
                                               max_source_chars=signature["max_source_chars"], **(probe or {}))
    prompt_sha = sha256_bytes(json.dumps(prompt, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    key = cache_key(signature, prompt_sha)
    meta = {"candidate_origin": origin, "candidate_sha256": sha256_json(predicted),
            "gold_sha256": sha256_json(gold) if gold is not None else None,
            "source_sha256": actual, "mode": prompt["protocol"]["mode"],
            "source_truncated": metadata["source_truncated"]}
    kwargs = dict(gold=gold, max_source_chars=signature["max_source_chars"],
                  max_output_tokens=signature["max_output_tokens"],
                  timeout_seconds=signature["timeout_seconds"], noise_terms=noise_terms)
    kwargs.update(probe or {})
    entry = None if ignore_cache else cache.get(key)
    if entry is not None:
        report = jm.run_judge(source_bytes, predicted, provider, cached_response=entry["response"], **kwargs)
        assert report["prompt_sha256"] == prompt_sha
        return key, report, meta, False
    if not allow_call:
        return key, None, meta, False
    report = jm.run_judge(source_bytes, predicted, provider, **kwargs)
    assert report["prompt_sha256"] == prompt_sha
    if report.get("raw_content") is not None:
        # Provider answered; cache the response even if validation rejected it,
        # because revalidation is deterministic and must not repay the API.
        cache[key] = {"response": {"content": report["raw_content"], "usage": report.get("usage"),
                                   "model": report.get("model"), "finish_reason": report.get("finish_reason")},
                      "stored_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    return key, report, meta, True


def _assemble(manifest_path: Path, manifest_sha: str, signature: dict, provider_name: str,
              ignore_cache: bool, max_calls: int, made: int, rows: list,
              split_filter: str | None = None) -> dict:
    with_usage = [r["report"]["usage"] for r in rows if r.get("report") and r["report"].get("usage")]
    fresh_usage = [r["report"]["usage"] for r in rows if r.get("new_api_call") and r["report"].get("usage")]
    def total(usages):
        return {k: sum(u[k] for u in usages) for k in ("input_tokens", "output_tokens", "total_tokens")} if usages and all(usages) else None
    return {"tool": "run_rubrics_judge.py", "tool_sha256": sha256_bytes(Path(__file__).read_bytes()),
            "manifest": str(manifest_path), "manifest_sha256": manifest_sha, "signature": signature,
            "provider": provider_name, "split_filter": split_filter, "ignore_cache": ignore_cache, "max_calls": max_calls,
            "new_api_calls": made, "cache_hits": sum(bool(r.get("cache_hit")) for r in rows),
            "skipped_budget": sum(r["status"] == "skipped_budget" for r in rows),
            "usage_total_all_cases": total(with_usage), "usage_new_calls_only": total(fresh_usage),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "cases": rows,
            "note": "Judge scores are uncalibrated model judgements with checked evidence; not human labels, accuracy estimates, or training reward. Resume: rerun the same manifest with a new output filename; cached cases cost zero new calls."}


def run_batch(manifest_path: Path, provider, *, model="qwen3.8-27b", max_output_tokens=2200,
              max_source_chars=40000, timeout_seconds=90.0, max_calls=10, ignore_cache=False,
              cache_path: Path | None = None, report_path: Path | None = None,
              split_filter: str | None = None, judge_version: str = "1.2") -> dict:
    root = manifest_path.resolve().parent
    manifest = load_manifest(manifest_path)
    if split_filter is not None:
        if split_filter not in SPLITS: raise ValueError("Invalid split filter")
        manifest = dict(manifest, cases=[c for c in manifest["cases"] if c["split"] == split_filter])
        if not manifest["cases"]: raise ValueError("Split filter selected no cases")
    jm = _judge_module(judge_version)
    signature = config_signature(model, max_output_tokens, max_source_chars, timeout_seconds,
                                 judge_version=jm.JUDGE_VERSION)
    manifest_sha = sha256_bytes(manifest_path.read_bytes())
    cache_file = cache_path or manifest_path.with_name(manifest_path.name + ".judge_cache.json")
    cache = {}
    if cache_file.exists():
        cache = json.loads(cache_file.read_text(encoding="utf-8"))
        if not isinstance(cache, dict):
            raise ValueError("Judge cache file must be a JSON object")
    rows, made = [], 0
    for case in manifest["cases"]:
        row = {"case_id": case["case_id"], "template": case["template"], "split": case["split"],
               "status": "pending", "cache_hit": False, "new_api_call": False, "case_meta": None, "report": None}
        try:
            _key, report, meta, called = run_case(case, root, provider, signature, cache,
                                                  ignore_cache, allow_call=made < max_calls,
                                                  judge_module=jm)
            if report is None:
                row.update(status="skipped_budget", case_meta=meta)
            else:
                if called:
                    made += 1
                row.update(status=report["status"], cache_hit=bool(report.get("cached")),
                           new_api_call=called, case_meta=meta, report=report)
        except Exception as error:
            row.update(status="error", error={"type": type(error).__name__, "detail": str(error)})
        rows.append(row)
        _write_json(cache_file, cache)
        if report_path is not None:
            _write_json(report_path, _assemble(manifest_path, manifest_sha, signature, provider.name,
                                               ignore_cache, max_calls, made, rows, split_filter=split_filter))
    return _assemble(manifest_path, manifest_sha, signature, provider.name, ignore_cache, max_calls, made, rows, split_filter=split_filter)


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(path)


def _build_provider(model: str, timeout_seconds: float):
    from src.webextractor.rubrics_judge import QwenJudgeProvider
    # The provider clamps each request to min(its own timeout, per-call budget).
    # Pass the batch timeout explicitly so the declared budget is honored
    # (constructor default 30s silently capped large-prompt calls before).
    return QwenJudgeProvider(model=model, max_retries=0, timeout_seconds=timeout_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="qwen3.8-27b")
    parser.add_argument("--max-output-tokens", type=int, default=2200)
    parser.add_argument("--max-source-chars", type=int, default=40000)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--max-calls", type=int, default=10)
    parser.add_argument("--split", choices=SPLITS, default=None,
                        help="Run only cases in this split (frozen manifest file is unchanged)")
    parser.add_argument("--ignore-cache", action="store_true",
                        help="Force fresh API calls (stability reruns); cache is still updated")
    parser.add_argument("--judge-version", choices=("1.2", "1.4"), default="1.2",
                        help="Judge protocol: 1.2 byte-frozen default; 1.4 adjudicated anchors (P-F)")
    args = parser.parse_args()
    if args.output.exists():
        print("Output exists; choose a new filename. The manifest cache still resumes completed cases.", file=sys.stderr)
        return 3
    report = run_batch(args.manifest, _build_provider(args.model, args.timeout), model=args.model,
                       max_output_tokens=args.max_output_tokens, max_source_chars=args.max_source_chars,
                       timeout_seconds=args.timeout, max_calls=args.max_calls,
                       ignore_cache=args.ignore_cache, report_path=args.output,
                       split_filter=args.split, judge_version=args.judge_version)
    rows = [{"id": r["case_id"], "status": r["status"], "cache": r["cache_hit"],
             "decision": (r["report"]["assessment"]["decision"] if r.get("report") and r["report"].get("assessment") else None)}
            for r in report["cases"]]
    print(json.dumps({"output": str(args.output), "new_api_calls": report["new_api_calls"],
                      "usage_new_calls_only": report["usage_new_calls_only"], "cases": rows}, ensure_ascii=False))
    if report["skipped_budget"]:
        return 4
    return 0 if all(r["status"] == "accepted" for r in report["cases"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
