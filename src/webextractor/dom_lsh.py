"""Deterministic MinHash + LSH banding over structural feature sets.

Zero model calls, zero network. Sub-quadratic candidate generation for template
clustering (amortizes future per-page inference cost). Final clustering uses
exact Jaccard in dom_cluster; LSH only proposes candidate pairs (recall-oriented).
"""
from __future__ import annotations

import hashlib
from itertools import combinations

MERSENNE_PRIME = (1 << 61) - 1
MAX_HASH = (1 << 32) - 1
DEFAULT_NUM_PERM = 128
DEFAULT_SEED = 20261123


def _feature_hash(feature: str) -> int:
    return int.from_bytes(hashlib.sha256(feature.encode('utf-8')).digest()[:4], 'big')


def _perm_params(num_perm: int, seed: int):
    params = []
    for i in range(num_perm):
        h = hashlib.sha256(('%d:%d' % (seed, i)).encode('utf-8')).digest()
        a = int.from_bytes(h[:8], 'big') % MERSENNE_PRIME
        b = int.from_bytes(h[8:16], 'big') % MERSENNE_PRIME
        params.append((a or 1, b))
    return params


def minhash_signature(features, num_perm: int = DEFAULT_NUM_PERM,
                      seed: int = DEFAULT_SEED) -> tuple:
    """Deterministic MinHash signature of a feature iterable (set semantics)."""
    if type(num_perm) is not int or num_perm <= 0:
        raise ValueError('num_perm must be a positive int')
    feats = set(features)
    params = _perm_params(num_perm, seed)
    if not feats:
        return tuple([MAX_HASH] * num_perm)
    hashes = [_feature_hash(f) for f in feats]
    sig = []
    for a, b in params:
        m = MAX_HASH
        for h in hashes:
            v = ((a * h + b) % MERSENNE_PRIME) & MAX_HASH
            if v < m:
                m = v
        sig.append(m)
    return tuple(sig)


def lsh_candidate_pairs(signatures: dict, bands: int = 16, rows: int = 8) -> set:
    """Candidate pairs via LSH banding. bands*rows must equal signature length."""
    ids = sorted(signatures)
    if not ids:
        return set()
    num_perm = len(signatures[ids[0]])
    if type(bands) is not int or type(rows) is not int or bands <= 0 or rows <= 0:
        raise ValueError('bands and rows must be positive ints')
    if bands * rows != num_perm:
        raise ValueError('bands*rows must equal signature length (%d)' % num_perm)
    for s in signatures.values():
        if len(s) != num_perm:
            raise ValueError('signature length mismatch')
    buckets = {}
    for pid in ids:
        sig = signatures[pid]
        for b in range(bands):
            band = sig[b * rows:(b + 1) * rows]
            key = (b, hashlib.sha256(repr(band).encode('utf-8')).digest())
            buckets.setdefault(key, []).append(pid)
    pairs = set()
    for members in buckets.values():
        for a, b in combinations(sorted(members), 2):
            pairs.add((a, b))
    return pairs


def estimated_jaccard(sig_a: tuple, sig_b: tuple) -> float:
    """MinHash Jaccard estimate (fraction of equal signature positions)."""
    if len(sig_a) != len(sig_a) or not sig_a:
        return 0.0
    return sum(x == y for x, y in zip(sig_a, sig_b)) / len(sig_a)
