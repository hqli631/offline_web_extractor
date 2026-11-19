from __future__ import annotations

from copy import deepcopy
import re
from dataclasses import asdict, dataclass
from typing import Any

from lxml import html
from lxml.html import HtmlElement

from .content_blocks import (ContentBlock, FOOTNOTE_PREDICATE, block_to_dict,
                             extract_blocks, normalize_heading_text, render_blocks)


NOISE_XPATH = (
    ".//script | .//style | .//noscript | .//template | .//nav | .//footer | "
    ".//section[contains(concat(' ', normalize-space(@class), ' '), ' translation-info ') or "
    "contains(concat(' ', normalize-space(@class), ' '), ' doc-note-translation ')] | "
    ".//*[contains(concat(' ', normalize-space(@class), ' '), ' translation-banner ')] | "
    ".//*[contains(concat(' ', normalize-space(@class), ' '), ' reference-toc ')] | "
    ".//*[contains(concat(' ', normalize-space(@class), ' '), ' prev-next ')] | "
    ".//*[contains(concat(' ', normalize-space(@class), ' '), ' article-footer ')] | "
    ".//aside[not(" + FOOTNOTE_PREDICATE + " or ("
    "contains(concat(' ', normalize-space(@class), ' '), ' footnote-list ') "
    "and descendant::*[" + FOOTNOTE_PREDICATE + "] ) or "
    "contains(concat(' ', normalize-space(@class), ' '), ' box-full ') or "
    "ancestor::details[@id='examples'])] | "
    ".//*[contains(concat(' ', normalize-space(@class), ' '), ' ad ')] | "
    ".//*[contains(concat(' ', normalize-space(@class), ' '), ' ads ')] | "
    ".//*[contains(concat(' ', normalize-space(@class), ' '), ' related ')] | "
    ".//*[contains(concat(' ', normalize-space(@class), ' '), ' recommend ')] | "
    ".//*[contains(concat(' ', normalize-space(@class), ' '), ' comment ')] | "
    ".//*[contains(concat(' ', normalize-space(@class), ' '), ' comments ')] | "
    ".//*[contains(concat(' ', normalize-space(@class), ' '), ' breadcrumb ')]"
)


@dataclass(frozen=True)
class CandidateDiagnostic:
    tag: str
    identifier: str
    xpath: str
    text_length: int
    paragraph_count: int
    link_ratio: float
    score: float


@dataclass
class ExtractionResult:
    status: str
    title: str
    paragraphs: list[str]
    body: str
    selected_candidate: CandidateDiagnostic | None
    candidates: list[CandidateDiagnostic]
    blocks: list[ContentBlock]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["blocks"] = [block_to_dict(block) for block in self.blocks]
        return result


def normalize_text(node: HtmlElement) -> str:
    return " ".join("".join(node.itertext()).split())


def remove_noise(node: HtmlElement) -> HtmlElement:
    for noise in node.xpath(NOISE_XPATH):
        parent = noise.getparent()
        if parent is not None:
            noise.drop_tree()  # Preserve正文 in the removed element's tail.
    return node


def link_ratio(node: HtmlElement) -> float:
    total = len(normalize_text(node))
    if total == 0:
        return 0.0
    linked = sum(len(normalize_text(anchor)) for anchor in node.xpath(".//a"))
    return linked / total


def candidate_score(node: HtmlElement) -> float:
    clean = remove_noise(deepcopy(node))
    text = normalize_text(clean)
    paragraphs = clean.xpath(".//p")
    identifier = f"{node.get('class', '')} {node.get('id', '')}".lower()
    tokens = set(re.split(r"[\s_-]+", identifier))

    score = min(len(text) / 100.0, 30.0)
    score += min(len(paragraphs) * 2.0, 15.0)
    for word in ("article", "content", "post", "body"):
        if word in tokens:
            score += 5.0
    for word in ("comment", "comments", "related", "recommend", "footer", "nav", "ad", "ads"):
        if word in tokens:
            score -= 15.0

    ratio = link_ratio(clean)
    if ratio > 0.5:
        score -= 15.0
    elif ratio > 0.3:
        score -= 8.0
    return round(score, 4)


def _candidate_nodes(tree: HtmlElement) -> list[HtmlElement]:
    nodes = tree.xpath(
        "//article | //main | //*[@role='main'] | "
        "//div[contains(concat(' ', normalize-space(@class), ' '), ' content ')] | "
        "//div[contains(concat(' ', normalize-space(@class), ' '), ' article-body ')] | "
        "//div[contains(concat(' ', normalize-space(@class), ' '), ' post-content ')]"
    )
    # XPath union already deduplicates nodes and preserves document order.
    return nodes


def _diagnostic(node: HtmlElement) -> CandidateDiagnostic:
    clean = remove_noise(deepcopy(node))
    identifier = f"{node.tag} class={node.get('class', '')} id={node.get('id', '')}"
    return CandidateDiagnostic(
        tag=node.tag,
        identifier=identifier,
        xpath=node.getroottree().getpath(node),
        text_length=len(normalize_text(clean)),
        paragraph_count=len(clean.xpath(".//p")),
        link_ratio=round(link_ratio(clean), 4),
        score=candidate_score(node),
    )


def normalize_title(node: HtmlElement) -> str:
    """Remove heading permalink controls while preserving actual title text."""
    return normalize_heading_text(node)


def _find_title(node: HtmlElement, tree: HtmlElement) -> str:
    """Find the title near a selected content node.

    A scoring candidate can be a content ``div`` whose title lives in its
    ancestor ``article`` or ``main``. Prefer that nearby title over an
    unrelated page heading.
    """
    local_titles = node.xpath(".//h1")
    if local_titles:
        return normalize_title(local_titles[0])

    for ancestor in node.iterancestors():
        if ancestor.tag in {"article", "main", "body"} or ancestor.get("role") == "main":
            ancestor_titles = ancestor.xpath(".//h1")
            if ancestor_titles:
                return normalize_title(ancestor_titles[0])

    page_titles = tree.xpath("//h1")
    return normalize_title(page_titles[0]) if page_titles else ""


def extract_html(source: str | bytes, *, container_xpath: str | None = None) -> ExtractionResult:
    if not source.strip():
        return ExtractionResult("empty_input", "", [], "", None, [], [])
    tree = html.fromstring(source, parser=html.HTMLParser(no_network=True))
    candidates = tree.xpath(container_xpath) if container_xpath else _candidate_nodes(tree)
    if not isinstance(candidates, list) or any(not isinstance(node, HtmlElement) for node in candidates):
        raise ValueError("container_xpath must select HTML elements, not text or scalar values")
    diagnostics = [_diagnostic(node) for node in candidates]
    if not candidates:
        return ExtractionResult("no_candidate", "", [], "", None, diagnostics, [])

    best_index = max(range(len(candidates)), key=lambda index: diagnostics[index].score)
    clean = remove_noise(deepcopy(candidates[best_index]))

    title = _find_title(candidates[best_index], tree)
    paragraphs = [normalize_text(node) for node in clean.xpath(".//p")]
    paragraphs = [paragraph for paragraph in paragraphs if paragraph]
    blocks = extract_blocks(clean)

    return ExtractionResult(
        status="ok" if blocks else "empty_body",
        title=title,
        paragraphs=paragraphs,
        body=render_blocks(blocks),
        selected_candidate=diagnostics[best_index],
        candidates=diagnostics,
        blocks=blocks,
    )
