from __future__ import annotations
from collections import Counter
from statistics import mean
import re

# Keep Chinese characters individually comparable while retaining Latin words
# and numbers as units.  This is a quality diagnostic, not a language model
# tokenizer; the report always keeps the continuous precision/recall too.
_TOKEN = re.compile(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+|[^\s]", re.UNICODE)

def _tokens(text): return _TOKEN.findall(text or "")
def _blocks(doc): return doc.get("blocks", []) if isinstance(doc, dict) else []
def _annotated(gold): return isinstance(gold, dict) and isinstance(gold.get("blocks"), list)
def _unscored(): return {"score": None, "reason": "No block annotation supplied"}
def _bucket(value):
    return 4 if value >= .98 else 3 if value >= .90 else 2 if value >= .70 else 1 if value >= .40 else 0

def completeness_score(predicted, gold):
    if not _annotated(gold):
        return _unscored()
    p = Counter(t for b in _blocks(predicted) for t in _tokens(b.get("text", "")))
    g = Counter(t for b in _blocks(gold) for t in _tokens(b.get("text", "")))
    matched = sum((p & g).values())
    recall = matched / sum(g.values()) if g else 1.0
    precision = matched / sum(p.values()) if p else (1.0 if not g else 0.0)
    return {"score": _bucket(recall), "recall": recall, "precision": precision}

def cleanliness_score(predicted, gold, noise_terms=()):
    if not _annotated(gold):
        return _unscored()
    text = "\n".join(b.get("text", "") for b in _blocks(predicted))
    expected = "\n".join(b.get("text", "") for b in _blocks(gold))
    # A legitimate occurrence in the reference does not become noise merely
    # because its wording looks suspicious. Count only excess occurrences.
    hits = sum(max(0, text.casefold().count(str(x).casefold()) -
                   expected.casefold().count(str(x).casefold()))
               for x in set(noise_terms) if str(x))
    p, g = Counter(_tokens(text)), Counter(_tokens(expected))
    matched = sum((p & g).values())
    precision = matched / sum(p.values()) if p else (1.0 if not g else 0.0)
    extra = sum((p - g).values())
    ratio = max(0.0, precision - hits * .25)
    return {"score": _bucket(ratio), "clean_ratio": ratio, "precision": precision,
            "noise_hits": hits, "extra_tokens": extra}

def _signature(block):
    # Use text to align blocks so swapping two ordinary paragraphs is visible.
    # Code retains whitespace; ordinary prose follows extractor normalization.
    text = block.get('text', '')
    if block.get('kind') != 'code':
        text = ' '.join(text.split())
    return (text,) + tuple(block.get(key) for key in
                 ("kind", "list_type", "depth", "ordinal", "heading_level", "footnote_label", "source_id"))


def _lcs_length(left, right):
    row = [0] * (len(right) + 1)
    for item in left:
        previous = 0
        for index, other in enumerate(right, 1):
            saved = row[index]
            if item == other:
                row[index] = previous + 1
            else:
                row[index] = max(row[index], row[index - 1])
            previous = saved
    return row[-1]


def structure_score(predicted, gold):
    if not _annotated(gold):
        return _unscored()
    pb, gb = _blocks(predicted), _blocks(gold)
    left, right = [_signature(block) for block in pb], [_signature(block) for block in gb]
    lcs = _lcs_length(left, right)
    ratio = (2 * lcs / (len(left) + len(right))) if left or right else 1.0
    return {"score": _bucket(ratio), "structure_ratio": ratio,
            "ordered_signature_lcs": lcs,
            "block_count_predicted": len(pb), "block_count_gold": len(gb)}

def score(predicted, gold, *, noise_terms=()):
    dimensions = {"completeness": completeness_score(predicted, gold), "cleanliness": cleanliness_score(predicted, gold, noise_terms), "structure": structure_score(predicted, gold)}
    measured = [d['score'] for d in dimensions.values() if d['score'] is not None]
    return {"dimensions": dimensions, "overall": round(mean(measured), 3) if measured else None,
            "title_exact": predicted.get("title") == gold.get("title") if 'title' in gold else None,
            "note": "Deterministic reference-based diagnostics; not a human or model quality judgement"}

def mean_absolute_difference(left, right):
    if len(left) != len(right) or not left: raise ValueError("Label lists must have equal nonzero length")
    return mean(abs(float(a["score"]) - float(b["score"])) for a, b in zip(left, right))

def repeatability(labels, repeats):
    return {"mean_absolute_difference": (mean(mean_absolute_difference(labels, other) for other in repeats)
                                          if repeats else None),
            "repeats": len(repeats),
            "note": "No repeat labels means agreement is unmeasured" if not repeats else None}
