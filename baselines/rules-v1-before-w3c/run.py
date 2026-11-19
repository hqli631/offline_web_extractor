"""Launch the learning project without requiring PowerShell scripts."""

import argparse
from pathlib import Path
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the offline webpage extraction project")
    commands = parser.add_subparsers(dest="action", required=True)
    extract = commands.add_parser("extract", help="extract a local HTML file")
    extract.add_argument("input", nargs="?", default="samples/python_blurb.html")
    extract.add_argument("--xpath")
    extract.add_argument("--output")
    extract.add_argument("--text-output")
    extract.add_argument("--show-candidates", action="store_true")
    evaluate = commands.add_parser("evaluate", help="compare with expected正文")
    evaluate.add_argument("input", nargs="?", default="samples/python_blurb.html")
    evaluate.add_argument("--expected", default="samples/python_blurb.expected.json")
    evaluate.add_argument("--output")
    inspect = commands.add_parser("inspect", help="inspect matched DOM elements and their ancestors")
    inspect.add_argument("input", nargs="?", default="samples/python_appetite_zh.html")
    inspect.add_argument("--xpath", default="//h1")
    inspect.add_argument("--limit", type=int, default=5)
    inspect.add_argument("--ancestors", action="store_true")
    batch = commands.add_parser("batch", help="evaluate multiple frozen webpages")
    batch.add_argument("manifest", nargs="?", default="samples/evaluation_manifest.json")
    batch.add_argument("--output", default="outputs/batch_report.json")
    batch.add_argument("--report", default="outputs/batch_report.md")
    reuse = commands.add_parser("reuse", help="apply one frozen rule across same-layout pages")
    reuse.add_argument("config", nargs="?", default="samples/sphinx_reuse.json")
    reuse.add_argument("--output-dir", default="outputs/rule_reuse")
    commands.add_parser("test", help="run the regression suite")
    args = parser.parse_args()

    if args.action == "test":
        arguments = ["-m", "unittest", "discover", "-s", "tests", "-v"]
    elif args.action == "reuse":
        arguments = ["-m", "src.webextractor.rule_reuse", args.config, "--output-dir", args.output_dir]
    elif args.action == "batch":
        arguments = ["-m", "src.webextractor.batch_evaluate", args.manifest,
                     "--output", args.output, "--report", args.report]
    elif args.action == "inspect":
        arguments = ["-m", "src.webextractor.inspect_dom", args.input,
                     "--xpath", args.xpath, "--limit", str(args.limit)]
        if args.ancestors:
            arguments.append("--ancestors")
    elif args.action == "extract":
        arguments = ["-m", "src.webextractor.cli", args.input]
        for name in ("xpath", "output", "text_output"):
            value = getattr(args, name)
            if value:
                arguments.extend(["--" + name.replace("_", "-"), value])
        if args.show_candidates:
            arguments.append("--show-candidates")
    else:
        arguments = ["-m", "src.webextractor.evaluate", args.input, args.expected]
        if args.output:
            arguments.extend(["--output", args.output])

    return subprocess.run(
        [sys.executable, *arguments], cwd=Path(__file__).resolve().parent, check=False
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
