from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from lxml import html


ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "samples/clustering/python-datastructures.html"
OLD_METADATA = ROOT / "samples/clustering/python-datastructures.html.source.json"
NEW_METADATA = ROOT / "samples/clustering/python-datastructures.html.source.v2.json"


def main() -> int:
    payload = HTML_PATH.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()

    old = json.loads(OLD_METADATA.read_text(encoding="utf-8-sig"))

    parser = html.HTMLParser(
        encoding="utf-8",
        no_network=True,
        recover=True,
    )
    document = html.document_fromstring(payload, parser=parser)

    title_nodes = document.xpath("//title")
    h1_nodes = document.xpath("//h1")

    if not title_nodes:
        raise ValueError("HTML does not contain a title")

    title = " ".join("".join(title_nodes[0].itertext()).split())
    headings = [
        " ".join("".join(node.itertext()).split())
        for node in h1_nodes
    ]

    if digest != old["sha256"]:
        raise ValueError("HTML hash differs from the original metadata")

    metadata = {
        "metadata_version": 2,
        "requested_url": old["requested_url"],
        "final_url": old["final_url"],
        "fetched_at": old["fetched_at"],
        "metadata_repaired_at": datetime.now(timezone.utc).isoformat(),
        "http_status": old["http_status"],
        "content_type": old["content_type"],
        "charset": "utf-8",
        "decoded_with": "lxml.HTMLParser(encoding='utf-8')",
        "sha256": digest,
        "bytes": len(payload),
        "source_kind": old["source_kind"],
        "split": old["split"],
        "proposed_manual_group": old["proposed_manual_group"],
        "page_title": title,
        "h1_texts": headings,
        "previous_metadata": OLD_METADATA.name,
        "note": (
            "Complete HTTP response, no truncation or production extraction. "
            "Metadata v2 repairs title decoding only; HTML bytes are unchanged. "
            "Group labels require source-structure review."
        ),
    }

    if NEW_METADATA.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing file: {NEW_METADATA}"
        )

    NEW_METADATA.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "html": str(HTML_PATH),
        "old_metadata": str(OLD_METADATA),
        "new_metadata": str(NEW_METADATA),
        "sha256": digest,
        "page_title": title,
        "h1_texts": headings,
    }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())