"""Opt-in text-density fallback for site-private containers (P-H H3).

extract_html stays BYTE-FROZEN (27-snapshot regression pinned). This module
adds extract_with_density_fallback(source): run extract_html first; ONLY when
its status is no_candidate or empty_body does a site-agnostic density pass
fire (classic table/private-container layouts, e.g. openbsd.org). Candidates:
div/section/td/main/article/body (bare-body classic layouts, e.g. openbsd.org); require >=200 non-noise chars and link ratio
<=0.5; score = text_len * (1 - link_ratio); deepest sufficient container wins
(ancestor dropped when a passing descendant retains >=90% of its score);
noise removed then extract_blocks. Pages extract_html already handles return the IDENTICAL
result object (zero drift by construction). Not wired into the frozen
rule_cache.fallback_extract; future loops opt in (P-E plan item, disclosed).
"""
from copy import deepcopy

from lxml import html

from .extractor import (ExtractionResult, _title_node, extract_html, link_ratio,
                        normalize_text, normalize_title, remove_noise)
from .content_blocks import extract_blocks, render_blocks

FALLBACK_STATUSES = ('no_candidate', 'empty_body')
MIN_TEXT_CHARS = 200
MAX_LINK_RATIO = 0.5
DENSITY_XPATH = '//div | //section | //td | //main | //article | //body'


def extract_with_density_fallback(source):
    base = extract_html(source)
    if base.status not in FALLBACK_STATUSES:
        return base
    if isinstance(source, bytes):
        text_source = source.decode('utf-8', errors='replace')
    else:
        text_source = source
    if not text_source.strip():
        return base
    tree = html.fromstring(text_source, parser=html.HTMLParser(no_network=True))
    passing = []
    for node in tree.xpath(DENSITY_XPATH):
        clean = remove_noise(deepcopy(node))
        text = normalize_text(clean)
        if len(text) < MIN_TEXT_CHARS:
            continue
        ratio = link_ratio(clean)
        if ratio > MAX_LINK_RATIO:
            continue
        passing.append((node, clean, len(text) * (1.0 - ratio)))
    # Deepest sufficient container: drop an ancestor when a passing descendant
    # retains >=90% of its density score (table layouts: td beats whole body).
    specific = []
    for node, clean, score in passing:
        descendants = set(node.iter())
        dominated = any(other is not node and other in descendants and oscore >= 0.9 * score
                        for other, _oclean, oscore in passing)
        if not dominated:
            specific.append((clean, score))
    if not specific:
        return base
    best, best_score = max(specific, key=lambda item: item[1])
    blocks = extract_blocks(best)
    if not blocks:
        return base
    title_node = _title_node(best, tree)
    title = normalize_title(title_node) if title_node is not None else ''
    paragraphs = [normalize_text(node) for node in best.xpath('.//p')]
    paragraphs = [p for p in paragraphs if p]
    return ExtractionResult(
        status='ok',
        title=title,
        paragraphs=paragraphs,
        body=render_blocks(blocks),
        selected_candidate=None,
        candidates=[],
        blocks=blocks,
    )
