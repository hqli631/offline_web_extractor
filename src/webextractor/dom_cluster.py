"""Complete-linkage agglomerative clustering (anti-chaining) over DOM features.

Connected components (dom_similarity) can chain A-B-C even when A-C < threshold.
Complete-linkage merges two clusters only if EVERY cross pair >= threshold, so
every intra-cluster pair >= threshold by construction (no chaining). Zero calls.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations


def multiset_jaccard(a: Counter, b: Counter) -> float:
    """Multiset Jaccard = sum(min counts) / sum(max counts); empty/empty = 1."""
    if not a and not b:
        return 1.0
    inter = sum((a & b).values())
    union = sum((a | b).values())
    return inter / union if union else 1.0


def pairwise_similarity(features_by_id: dict) -> dict:
    ids = sorted(features_by_id)
    return {(a, b): multiset_jaccard(features_by_id[a], features_by_id[b])
            for a, b in combinations(ids, 2)}


def _sim(sim: dict, a: str, b: str) -> float:
    if a == b:
        return 1.0
    return sim[(a, b) if a < b else (b, a)]


def complete_linkage(features_by_id: dict, threshold: float, sim: dict | None = None) -> dict:
    """Agglomerative complete-linkage with a frozen threshold cutoff.

    Greedily merge the cluster pair with the highest min-cross-pair similarity
    while that value >= threshold. Guarantees every intra-cluster pair >= threshold.
    """
    if not (0.0 <= threshold <= 1.0):
        raise ValueError('threshold must be in [0,1]')
    ids = sorted(features_by_id)
    if sim is None:
        sim = pairwise_similarity(features_by_id)
    clusters = [[i] for i in ids]
    merges = []
    while len(clusters) > 1:
        best, best_val = None, -1.0
        for i, j in combinations(range(len(clusters)), 2):
            cross_min = min(_sim(sim, a, b) for a in clusters[i] for b in clusters[j])
            if cross_min > best_val:
                best_val, best = cross_min, (i, j)
        if best is None or best_val < threshold:
            break
        i, j = best
        merges.append({'merged': [sorted(clusters[i]), sorted(clusters[j])],
                       'min_cross_similarity': round(best_val, 6)})
        clusters[i] = sorted(clusters[i] + clusters[j])
        del clusters[j]
    diag, violations = [], []
    for c in clusters:
        if len(c) > 1:
            intra = [_sim(sim, a, b) for a, b in combinations(c, 2)]
            diag.append({'cluster': c, 'size': len(c),
                         'min_intra_similarity': round(min(intra), 6)})
            for a, b in combinations(c, 2):
                if _sim(sim, a, b) < threshold:
                    violations.append({'pair': [a, b], 'similarity': _sim(sim, a, b)})
        else:
            diag.append({'cluster': c, 'size': 1, 'min_intra_similarity': 1.0})
    return {'clusters': clusters, 'merges': merges, 'cluster_diagnostics': diag,
            'threshold': threshold, 'anti_chaining_violations': violations,
            'guarantee': 'every intra-cluster pair >= threshold (complete-linkage)'}
