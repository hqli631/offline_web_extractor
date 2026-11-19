"""Read-only DOM inspection for learning XPath on real HTML snapshots."""

import argparse
import json
from pathlib import Path
import sys

from lxml import etree, html
from lxml.html import HtmlElement

from .extractor import normalize_text


def describe(node: HtmlElement) -> dict:
    text = normalize_text(node)
    return {
        "tag": node.tag,
        "id": node.get("id"),
        "class": node.get("class"),
        "role": node.get("role"),
        "xpath": node.getroottree().getpath(node),
        "paragraph_count": len(node.xpath(".//p")),
        "text_length": len(text),
        "preview": text[:160],
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Inspect raw parsed DOM without deleting any nodes")
    parser.add_argument("input", type=Path)
    parser.add_argument("--xpath", default="//h1")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--ancestors", action="store_true")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be at least 1")
    try:
        tree = html.fromstring(args.input.read_bytes(), parser=html.HTMLParser(no_network=True))
        matches = tree.xpath(args.xpath)
    except (OSError, etree.LxmlError) as error:
        parser.error(str(error))
    if not isinstance(matches, list) or any(not isinstance(n, HtmlElement) for n in matches):
        parser.error("--xpath must select elements, not text or scalar values")
    items = []
    for node in matches[:args.limit]:
        item = describe(node)
        if args.ancestors:
            item["ancestors_nearest_first"] = [describe(n) for n in node.iterancestors()]
        items.append(item)
    print(json.dumps({
        "match_count": len(matches),
        "shown_count": len(items),
        "note": "Raw DOM counts before noise removal; preview is truncated.",
        "matches": items,
    }, ensure_ascii=False, indent=2))
    return 0 if matches else 2


if __name__ == "__main__":
    raise SystemExit(main())
