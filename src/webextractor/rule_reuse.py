"""Apply one frozen container XPath to reference and transfer snapshots."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

from lxml import etree, html
from lxml.html import HtmlElement

from .extractor import extract_html


def run_reuse(config_path: Path) -> dict:
    source_before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(Path(__file__).parent.glob('*.py'))}
    config_path = config_path.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    rule = config["rule"]
    expression = rule["container_xpath"]
    try:
        query = etree.XPath(expression)
        probe = query(html.fromstring('<html><body><div role="main"><p>probe</p></div></body></html>'))
        if not isinstance(probe, list) or any(not isinstance(n, HtmlElement) for n in probe):
            raise ValueError("container_xpath must select elements, not text or scalar values")
    except etree.XPathError as error:
        raise ValueError(f"Invalid container XPath: {error}") from error
    rule_hash = hashlib.sha256(json.dumps(rule, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    rows = []
    seen = set()
    for page in config["pages"]:
        row = {"id": page["id"], "role": page["role"], "match_count": None,
               "extraction": None, "error": None, "coverage_notes": {}, "quality": None}
        try:
            if not re.fullmatch(r"[a-zA-Z0-9_-]+", page["id"]) or page["id"] in seen:
                raise ValueError("Page id must be unique and contain letters, digits, underscores or hyphens")
            seen.add(page["id"])
            if page["role"] not in {"reference", "transfer"}:
                raise ValueError("Page role must be reference or transfer")
            source = (config_path.parent / page["html"]).read_bytes()
            actual_hash = hashlib.sha256(source).hexdigest()
            row["snapshot_sha256"] = actual_hash
            if actual_hash != page["sha256"].lower():
                raise ValueError("Snapshot SHA256 mismatch")
            expected = None
            if page.get('expected'):
                expected_bytes = (config_path.parent / page['expected']).read_bytes()
                expected_hash = hashlib.sha256(expected_bytes).hexdigest()
                if expected_hash != page['expected_sha256'].lower():
                    raise ValueError('Expected SHA256 mismatch')
                expected = json.loads(expected_bytes.decode('utf-8-sig'))
                row['expected_sha256'] = expected_hash
            tree = html.fromstring(source, parser=html.HTMLParser(no_network=True))
            matches = query(tree)
            if not isinstance(matches, list) or any(not isinstance(n, HtmlElement) for n in matches):
                raise ValueError("container_xpath must select HTML elements")
            row["match_count"] = len(matches)
            if len(matches) != 1:
                row["status"] = "rule_no_match" if not matches else "rule_ambiguous"
            else:
                result = extract_html(source, container_xpath=expression).to_dict()
                row.update(status=result["status"], extraction=result)
                if expected is not None:
                    predicted_text = Counter(b['text'] for b in result['blocks'])
                    expected_text = Counter(b['text'] for b in expected['blocks'])
                    matched = sum((predicted_text & expected_text).values())
                    row['quality'] = {
                        'title_exact': result['title'] == expected['title'],
                        'blocks_exact': result['blocks'] == expected['blocks'],
                        'block_text_precision': matched / sum(predicted_text.values()) if predicted_text else float(not expected_text),
                        'block_text_recall': matched / sum(expected_text.values()) if expected_text else float(not predicted_text),
                        'missing_text_blocks': list((expected_text - predicted_text).elements()),
                        'extra_text_blocks': list((predicted_text - expected_text).elements()),
                        'note': 'Text counters ignore order and structure; blocks_exact checks full ordered blocks. Runtime status stays separate from quality.',
                    }
                counts = Counter(n.tag for n in matches[0].iterdescendants() if isinstance(n.tag, str))
                row["coverage_notes"] = {
                    "raw_review_element_counts": {tag: counts[tag] for tag in ("table", "img") if counts[tag]},
                    "raw_subheading_count": sum(counts[tag] for tag in ("h2", "h3", "h4", "h5", "h6")),
                    "extracted_heading_count": sum(b["kind"] == "heading" for b in result["blocks"]),
                    "extracted_footnote_count": sum(b["kind"] == "footnote" for b in result["blocks"]),
                    "raw_pre_count": counts["pre"],
                    "extracted_code_count": sum(b["kind"] == "code" for b in result["blocks"]),
                    "raw_aside_count": counts["aside"],
                    "note": "Raw counts identify review targets, not quality scores. Basic tables, semantic/referenced notes and selected content asides are supported; image OCR is not. Quality is null if no complete reference was supplied.",
                }
        except Exception as error:
            row.update(status="error", error=f"{type(error).__name__}: {error}")
        rows.append(row)
    source_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(Path(__file__).parent.glob('*.py'))}
    if source_hashes != source_before:
        raise ValueError('Source changed during rule reuse; rerun after freezing code')
    return {"rule": rule, "rule_sha256": rule_hash, "pages": rows,
            'config_sha256': hashlib.sha256(config_path.read_bytes()).hexdigest(),
            'source_sha256': source_hashes,
            "note": "A unique container match proves only XPath applicability. It is not extraction accuracy, content completeness, or automatic clustering. No fallback or per-page rule repair is used."}


def render_summary(report: dict) -> str:
    lines = ["# 固定规则跨页复用", "", f"固定 XPath：`{report['rule']['container_xpath']}`", "",
             f"规则指纹：`{report['rule_sha256']}`", "",
             "| 页面 | 用途 | 匹配数 | 状态 | 标题 | 块数 |", "| --- | --- | ---: | --- | --- | ---: |"]
    for row in report["pages"]:
        result = row["extraction"]
        title = result["title"].replace("|", "&#124;") if result else "—"
        lines.append(f"| {row['id']} | {row['role']} | {row['match_count']} | {row['status']} | {title} | {len(result['blocks']) if result else 0} |")
    lines.extend(["", "容器唯一匹配只证明规则适用，不证明正文完整。quality为空表示没有完整参考；合成漂移与真实迁移必须分开报告。本工具不自动聚类、不回退、不逐页修规则。"])
    for row in report["pages"]:
        if row["error"]:
            lines.extend(["", f"{row['id']} 错误：{row['error']}"])
        if row.get('quality') is not None:
            quality = row['quality']
            lines.extend(['', f"{row['id']} 结构全匹配：{quality['blocks_exact']}；块文本P/R：{quality['block_text_precision']}/{quality['block_text_recall']}。"])
        counts = row["coverage_notes"].get("raw_review_element_counts", {})
        raw_pre = row["coverage_notes"].get("raw_pre_count", 0)
        if raw_pre:
            extracted = row["coverage_notes"]["extracted_code_count"]
            lines.extend(["", f"{row['id']} 原始容器有 {raw_pre} 个 pre，本次输出 {extracted} 个代码块；数量对应不代表文字/缩进已自动评分。"])
        if counts:
            lines.extend(["", f"{row['id']} 容器内待人工检查的原始标签：`{json.dumps(counts, ensure_ascii=False)}`。这些数量不是漏提块数。"])
        aside_count = row["coverage_notes"].get("raw_aside_count", 0)
        if aside_count:
            notes = row["coverage_notes"]["extracted_footnote_count"]
            lines.extend(["", f"{row['id']} 原始容器有 {aside_count} 个 aside（可能含包装层），本次保留 {notes} 个脚注块；部分正文旁注可保留，仍需核对边界。"])
        headings = row["coverage_notes"].get("raw_subheading_count", 0)
        if headings:
            extracted = row["coverage_notes"]["extracted_heading_count"]
            lines.extend(["", f"{row['id']} 原始容器有 {headings} 个h2–h6，本次输出 {extracted} 个带层级的子标题块。"])
    return "\n".join(lines) + "\n"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Reuse one frozen rule on multiple HTML snapshots")
    parser.add_argument("config", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/rule_reuse"))
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error('Output directory is not empty; use a new directory to preserve earlier experiments')
    try:
        report = run_reuse(args.config)
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = render_summary(report)
    (args.output_dir / "report.md").write_text(summary, encoding="utf-8")
    for row in report["pages"]:
        result = row["extraction"]
        if result:
            (args.output_dir / (row["id"] + ".md")).write_text("# " + result["title"] + "\n\n" + result["body"] + "\n", encoding="utf-8")
    print(summary)
    return 0 if all(r["status"] == "ok" for r in report["pages"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
