from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from .extractor import extract_html
from .content_blocks import block_to_dict


def _char_recall(predicted: str, expected: str) -> float:
    if not expected:
        return 1.0 if not predicted else 0.0
    matched = sum((Counter(predicted) & Counter(expected)).values())
    return min(matched / len(expected), 1.0)


def _char_precision(predicted: str, expected: str) -> float:
    if not predicted:
        return 1.0 if not expected else 0.0
    matched = sum((Counter(predicted) & Counter(expected)).values())
    return min(matched / len(predicted), 1.0)


def evaluate(html_path: Path, expected_path: Path) -> dict[str, object]:
    result = extract_html(html_path.read_bytes())
    expected = json.loads(expected_path.read_text(encoding="utf-8-sig"))
    predicted_body = "".join(result.paragraphs)
    expected_body = "".join(expected.get("paragraphs", []))
    expected_blocks = expected.get("blocks")
    block_precision = block_recall = None
    if expected_blocks is not None:
        predicted_texts = Counter(block.text for block in result.blocks)
        expected_texts = Counter(block["text"] for block in expected_blocks)
        matched = sum((predicted_texts & expected_texts).values())
        block_precision = matched / sum(predicted_texts.values()) if predicted_texts else float(not expected_texts)
        block_recall = matched / sum(expected_texts.values()) if expected_texts else float(not predicted_texts)
    return {
        "status": result.status,
        "title_exact": result.title == expected.get("title", ""),
        "block_text_precision": block_precision,
        "block_text_recall": block_recall,
        "body_exact": result.paragraphs == expected.get("paragraphs", []),
        "blocks_exact": ([block_to_dict(block) for block in result.blocks] == expected["blocks"]
                         if "blocks" in expected else None),
        "rendered_body_exact": (result.body == expected["body"] if "body" in expected else None),
        "evaluation_note": "body_exact compares legacy p paragraphs only; null structure metrics mean no structure annotation was supplied.",
        "body_char_recall_rough": round(_char_recall(predicted_body, expected_body), 4),
        "body_char_precision_rough": round(_char_precision(predicted_body, expected_body), 4),
        "predicted": result.to_dict(),
        "expected": expected,
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Evaluate one local HTML snapshot")
    parser.add_argument("html", type=Path)
    parser.add_argument("expected", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = json.dumps(evaluate(args.html, args.expected), ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
