"""Evaluate frozen snapshots, keeping development and validation separate."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

from .evaluate import evaluate


def run_batch(manifest_path: Path) -> dict:
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    rows = []
    seen = set()
    for case in manifest["cases"]:
        row = {key: case[key] for key in ("id", "split", "source_kind")}
        try:
            if case["id"] in seen:
                raise ValueError("Duplicate case id")
            seen.add(case["id"])
            if case["split"] not in {"development", "validation"} or case["source_kind"] not in {"real", "synthetic"}:
                raise ValueError("Invalid split or source_kind")
            snapshot = manifest_path.parent / case["html"]
            expected = manifest_path.parent / case["expected"]
            actual_hash = hashlib.sha256(snapshot.read_bytes()).hexdigest()
            if actual_hash.lower() != case["sha256"].lower():
                raise ValueError("Snapshot SHA256 mismatch: update/review annotations before scoring")
            metrics = evaluate(snapshot, expected)
            row.update(outcome="evaluated", metrics=metrics, error=None)
        except Exception as error:
            row.update(outcome="error", metrics=None, error=f"{type(error).__name__}: {error}")
        rows.append(row)

    groups = defaultdict(list)
    for row in rows:
        groups[row["split"], row["source_kind"]].append(row)
    summary = []
    for (split, source_kind), group in sorted(groups.items()):
        evaluated = [r["metrics"] for r in group if r["outcome"] == "evaluated"]
        structured = [m for m in evaluated if m["blocks_exact"] is not None]
        summary.append({
            "split": split, "source_kind": source_kind, "total": len(group),
            "evaluated": len(evaluated), "errors": len(group) - len(evaluated),
            "title_exact_rate": sum(m["title_exact"] for m in evaluated) / len(evaluated) if evaluated else None,
            "structure_scored": len(structured),
            "blocks_exact_rate": sum(m["blocks_exact"] for m in structured) / len(structured) if structured else None,
        })
    return {"manifest": str(manifest_path), "cases": rows, "summary": summary,
            "note": "Errors are reported separately. Do not merge synthetic/development cases into validation accuracy. Validation cases become development cases once used to tune rules."}


def render_report(report: dict) -> str:
    lines = ["# 网页批量评测", "", "开发、验证和合成样本分组统计；这是小样本诊断，不是总体准确率估计。", "",
             "| 分组 | 总数 | 已评分 | 错误 | 结构已标注 | 结构全匹配 |",
             "| --- | ---: | ---: | ---: | ---: | --- |"]
    for group in report["summary"]:
        rate = group["blocks_exact_rate"]
        lines.append(f"| {group['split']}/{group['source_kind']} | {group['total']} | {group['evaluated']} | {group['errors']} | {group['structure_scored']} | {rate if rate is not None else '未评分'} |")
    for row in report["cases"]:
        lines.extend(["", f"## {row['id']} ({row['split']}/{row['source_kind']})", ""])
        if row["outcome"] == "error":
            lines.append(row["error"])
            continue
        m = row["metrics"]
        lines.append(f"状态：{m['status']}；标题：{m['title_exact']}；旧p段落：{m['body_exact']}；结构：{m['blocks_exact']}；块文本精确率/召回率：{m['block_text_precision']}/{m['block_text_recall']}。")
        expected_blocks = m["expected"].get("blocks")
        if expected_blocks is not None:
            predicted_text = [b["text"] for b in m["predicted"]["blocks"]]
            expected_text = [b["text"] for b in expected_blocks]
            for label, difference in [("多提", Counter(predicted_text) - Counter(expected_text)), ("漏提", Counter(expected_text) - Counter(predicted_text))]:
                for text, count in difference.items():
                    lines.extend(["", f"{label}（{count}次）：", "", "    " + text.replace("\n", " " )])
            if predicted_text == expected_text and not m["blocks_exact"]:
                lines.extend(["", "块文字一致，但类型/列表元数据不一致，请对照 JSON。"])
    return "\n".join(lines) + "\n"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Run a manifest of frozen webpage cases")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, default=Path("outputs/batch_report.json"))
    parser.add_argument("--report", type=Path, default=Path("outputs/batch_report.md"))
    args = parser.parse_args()
    result = run_batch(args.manifest)
    for path, text in [(args.output, json.dumps(result, ensure_ascii=False, indent=2)),
                       (args.report, render_report(result))]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 1 if any(r["outcome"] == "error" for r in result["cases"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
