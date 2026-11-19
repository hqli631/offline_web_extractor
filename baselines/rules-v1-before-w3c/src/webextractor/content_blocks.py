"""Extract paragraphs and list items in DOM order, then render plain text."""

from dataclasses import asdict, dataclass
from copy import deepcopy
import re

from lxml.html import HtmlElement


FOOTNOTE_PREDICATE = (
    "@role='doc-footnote' or "
    "contains(concat(' ', normalize-space(@class), ' '), ' footnote ')"
)


@dataclass(frozen=True)
class ContentBlock:
    kind: str
    text: str
    list_type: str | None = None
    depth: int = 0
    ordinal: int | None = None
    heading_level: int | None = None
    footnote_label: str | None = None
    source_id: str | None = None


def block_to_dict(block: ContentBlock) -> dict:
    result = asdict(block)
    for name in ("heading_level", "footnote_label", "source_id"):
        if result[name] is None:
            del result[name]
    return result


def normalize_heading_text(node: HtmlElement) -> str:
    """Ignore permalink controls without discarding real inline heading text."""
    clean = deepcopy(node)
    for anchor in clean.xpath(
        ".//a[contains(concat(' ', normalize-space(@class), ' '), ' headerlink ')]"
    ):
        anchor.drop_tree()
    return " ".join("".join(clean.itertext()).split())


def code_text(node: HtmlElement) -> str:
    # itertext reads highlight spans and decodes entities, but leaves code
    # whitespace intact. Unlike ordinary paragraphs, do not split or strip it.
    return "".join(node.itertext())


def footnote_block(node: HtmlElement) -> ContentBlock | None:
    clean = deepcopy(node)
    labels = clean.xpath(".//span[contains(concat(' ', normalize-space(@class), ' '), ' label ')]")
    label = " ".join("".join(labels[0].itertext()).split()) if labels else None
    for control in clean.xpath(
        ".//span[contains(concat(' ', normalize-space(@class), ' '), ' label ')] | .//a[@role='doc-backlink']"
    ):
        if control.getparent() is not None:
            control.drop_tree()
    paragraphs = clean.xpath(".//p")
    texts = [" ".join("".join(p.itertext()).split()) for p in paragraphs]
    text = "\n\n".join(t for t in texts if t) if paragraphs else " ".join("".join(clean.itertext()).split())
    if not text:
        return None
    return ContentBlock("footnote", text, footnote_label=label, source_id=node.get("id"))


def extract_blocks(root: HtmlElement) -> list[ContentBlock]:
    blocks: list[ContentBlock] = []

    def visit(node: HtmlElement) -> None:
        if node.tag == "aside" and node.xpath("boolean(self::*[" + FOOTNOTE_PREDICATE + "])"):
            block = footnote_block(node)
            if block:
                blocks.append(block)
            return  # Its paragraphs belong to this footnote, not duplicated prose.
        if node.tag == "pre":
            text = code_text(node)
            if text.strip():
                blocks.append(ContentBlock("code", text))
            return
        if node.tag in {"h2", "h3", "h4", "h5", "h6"}:
            text = normalize_heading_text(node)
            if text:
                blocks.append(ContentBlock("heading", text, heading_level=int(node.tag[1])))
            return
        if node.tag == "p":
            text = " ".join("".join(node.itertext()).split())
            if text:
                blocks.append(ContentBlock("paragraph", text))
            return  # This paragraph's inline descendants have already been read.
        if node.tag in {"ul", "ol"}:
            visit_list(node, depth=0)
            return  # Do not visit li/p a second time.
        for child in node:
            visit(child)

    def integer_attribute(node: HtmlElement, name: str, default: int) -> int:
        try:
            return int(node.get(name, ""))
        except ValueError:
            return default

    def visit_list(node: HtmlElement, depth: int) -> None:
        items = node.xpath("./li")
        ordered = node.tag == "ol"
        reversed_order = ordered and "reversed" in node.attrib
        next_number = integer_attribute(node, "start", len(items) if reversed_order else 1)
        for item in items:
            number = integer_attribute(item, "value", next_number) if ordered else None
            visit_item(item, node.tag, depth, number)
            if ordered:
                next_number = number + (-1 if reversed_order else 1)

    def visit_item(item: HtmlElement, list_type: str, depth: int, number: int | None) -> None:
        fragments: list[str] = []
        started = False

        def flush() -> None:
            nonlocal started
            text = " ".join("".join(fragments).split())
            fragments.clear()
            if text:
                kind = "list_item_continuation" if started else "list_item"
                blocks.append(ContentBlock(kind, text, list_type, depth, number))
                started = True

        def consume(node: HtmlElement) -> None:
            if node.text:
                fragments.append(node.text)
            for child in node:
                if child.tag == "pre":
                    flush()
                    text = code_text(child)
                    if text.strip():
                        blocks.append(ContentBlock("code", text, list_type, depth, number))
                elif child.tag in {"ul", "ol"}:
                    flush()
                    visit_list(child, depth + 1)
                elif child.tag in {"p", "div"}:
                    flush()
                    consume(child)
                    flush()
                else:
                    consume(child)
                if child.tail:
                    fragments.append(child.tail)

        consume(item)
        flush()

    visit(root)
    return blocks


def render_blocks(blocks: list[ContentBlock]) -> str:
    lines: list[str] = []
    previous: ContentBlock | None = None
    for block in blocks:
        # Markdown soft line breaks do not separate paragraphs. A blank line
        # also closes a list before the following ordinary paragraph.
        if previous is not None and (block.kind in {"paragraph", "heading", "code", "footnote"}
                                     or previous.kind in {"paragraph", "heading", "code", "footnote"}):
            lines.append("")
        previous = block
        if block.kind == "paragraph":
            lines.append(block.text)
            continue
        if block.kind == "heading":
            lines.append("#" * (block.heading_level or 2) + " " + block.text)
            continue
        if block.kind == "footnote":
            lines.append((block.footnote_label + " " if block.footnote_label else "") + block.text)
            continue
        if block.kind == "code":
            # The closing fence must not occur inside the code itself.
            longest_run = max((len(run) for run in re.findall(r"`+", block.text)), default=0)
            fence = "`" * max(3, longest_run + 1)
            text = block.text
            if not text.endswith("\n"):
                text += "\n"  # Required before closing fence; blocks.text is unchanged.
            rendered = fence + "\n" + text + fence
            if block.list_type:
                marker = f"{block.ordinal}. " if block.list_type == "ol" else "- "
                indent = "  " * block.depth + " " * len(marker)
                rendered = "\n".join(indent + line for line in rendered.split("\n"))
            lines.append(rendered)
            continue
        marker = f"{block.ordinal}. " if block.list_type == "ol" else "- "
        indent = "  " * block.depth
        if block.kind == "list_item_continuation":
            lines.append(indent + " " * len(marker) + block.text)
        else:
            lines.append(indent + marker + block.text)
    return "\n".join(lines)
