from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .extractor import extract_html


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Extract正文 from a local HTML file")
    parser.add_argument("input", type=Path, help="local HTML file")
    parser.add_argument("--output", type=Path, help="write JSON result to this path")
    parser.add_argument("--text-output", type=Path, help="write readable title and正文")
    parser.add_argument("--show-candidates", action="store_true", help="print scoring diagnostics")
    parser.add_argument("--xpath", help="override automatic candidates with a container XPath")
    args = parser.parse_args()

    try:
        source = args.input.read_bytes()  # lxml detects HTML charset declarations.
    except FileNotFoundError:
        parser.error(f"Input HTML file does not exist: {args.input}. Create or save it before running extraction.")
    except OSError as error:
        parser.error(f"Cannot read input HTML: {error}")
    result = extract_html(source, container_xpath=args.xpath).to_dict()
    if args.text_output:
        args.text_output.parent.mkdir(parents=True, exist_ok=True)
        title = result["title"]
        if title and args.text_output.suffix.lower() == ".md":
            title = "# " + title
        document = (title + "\n\n" if title else "") + result["body"] + "\n"
        args.text_output.write_text(document, encoding="utf-8")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.show_candidates:
        print("\n候选节点诊断：")
        for item in result["candidates"]:
            print(json.dumps(item, ensure_ascii=False))
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
