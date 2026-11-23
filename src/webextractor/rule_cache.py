"""Cluster rule cache + fallback + drift detection (zero model calls).

Derives a shared container rule deterministically from a representative page
(structural heuristic, NOT an LLM), caches it per cluster, applies it to members
with structural validation (unique match + status ok + nonempty blocks), falls
back to per-page heuristic extraction on failure, and flags drift via TWO
mechanisms: (1) fingerprint distance to the representative below drift_threshold,
and (2) rule-execution failure (catches attribute drift such as role-drift that
tag-path fingerprints cannot see, since features exclude attributes).
"""
from __future__ import annotations

import hashlib
import json

from lxml import etree, html

from .agent_rules import validate_rule
from .dom_cluster import multiset_jaccard
from .extractor import extract_html

CONTAINER_SELECTORS = ("//*[@role='main']", '//main', '//article', "//div[@class='body']")
MIN_CONTAINER_TEXT = 50
DEFAULT_DRIFT_THRESHOLD = 0.7


def _tree(source):
    return html.fromstring(source, parser=html.HTMLParser(no_network=True))


def _elements(tree, xpath):
    try:
        matches = tree.xpath(xpath)
    except etree.XPathError:
        return []
    return [m for m in matches if isinstance(m, html.HtmlElement)]


def derive_shared_rule(source):
    """Deterministic unique-content-container selection; validated rule or None."""
    tree = _tree(source)
    for xpath in CONTAINER_SELECTORS:
        elems = _elements(tree, xpath)
        if len(elems) == 1 and len(elems[0].text_content().strip()) >= MIN_CONTAINER_TEXT:
            rule = {'version': 1, 'container_xpath': xpath, 'exclude_xpaths': []}
            try:
                return validate_rule(rule)
            except ValueError:
                continue
    return None


def apply_rule(source, rule):
    """Apply a frozen rule in-process; structural validation mirrors rule_reuse."""
    tree = _tree(source)
    try:
        matches = etree.XPath(rule['container_xpath'])(tree)
    except etree.XPathError:
        return {'status': 'rule_error', 'match_count': 0, 'extraction': None, 'block_count': 0}
    elems = [m for m in matches if isinstance(m, html.HtmlElement)]
    if not elems:
        return {'status': 'rule_no_match', 'match_count': 0, 'extraction': None, 'block_count': 0}
    if len(elems) > 1:
        return {'status': 'rule_ambiguous', 'match_count': len(elems), 'extraction': None, 'block_count': 0}
    result = extract_html(source, container_xpath=rule['container_xpath']).to_dict()
    return {'status': result['status'], 'match_count': 1, 'extraction': result,
            'block_count': len(result['blocks'])}


def fallback_extract(source):
    """Per-page heuristic extraction (no shared rule)."""
    result = extract_html(source).to_dict()
    return {'status': result['status'], 'extraction': result, 'block_count': len(result['blocks'])}


def cluster_fingerprint(features):
    return hashlib.sha256(json.dumps(sorted(features.items()), ensure_ascii=False).encode('utf-8')).hexdigest()


def _rule_sha(rule):
    if rule is None:
        return None
    return hashlib.sha256(json.dumps(rule, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


class ClusterRuleCache:
    def __init__(self, drift_threshold=DEFAULT_DRIFT_THRESHOLD):
        if not (0.0 <= drift_threshold <= 1.0):
            raise ValueError('drift_threshold must be in [0,1]')
        self.drift_threshold = drift_threshold
        self.entries = {}

    def derive_and_cache(self, cluster_id, rep_id, rep_source, rep_features):
        rule = derive_shared_rule(rep_source)
        entry = {'cluster_id': cluster_id, 'rep_id': rep_id, 'rule': rule,
                 'rule_sha256': _rule_sha(rule), 'rep_features': rep_features,
                 'fingerprint': cluster_fingerprint(rep_features)}
        self.entries[cluster_id] = entry
        return entry

    def reuse_member(self, cluster_id, member_id, member_source, member_features):
        entry = self.entries[cluster_id]
        sim = multiset_jaccard(member_features, entry['rep_features'])
        reasons = []
        if sim < self.drift_threshold:
            reasons.append('fingerprint_drift')
        rule = entry['rule']
        if rule is None:
            reasons.append('no_shared_rule')
            applied = {'status': 'no_rule', 'match_count': 0, 'extraction': None, 'block_count': 0}
        else:
            applied = apply_rule(member_source, rule)
            if applied['status'] != 'ok' or applied['block_count'] == 0:
                reasons.append('rule_failure')
        if reasons:
            fb = fallback_extract(member_source)
            return {'member_id': member_id, 'reuse': False, 'fallback': True, 'drift': True,
                    'drift_reasons': reasons, 'fingerprint_similarity': round(sim, 6),
                    'rule_status': applied['status'], 'extraction': fb['extraction'],
                    'final_status': fb['status'], 'block_count': fb['block_count']}
        return {'member_id': member_id, 'reuse': True, 'fallback': False, 'drift': False,
                'drift_reasons': [], 'fingerprint_similarity': round(sim, 6),
                'rule_status': applied['status'], 'extraction': applied['extraction'],
                'final_status': applied['status'], 'block_count': applied['block_count']}
