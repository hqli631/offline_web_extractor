"""Rubrics v2 reference diagnostics. No network or model judgement.

Text identities align blocks before attributes/order are measured. Unmatched
blocks limit structural coverage; they are never assumed structurally correct.
"""
from collections import Counter, defaultdict, deque
import re

from .rubrics import _tokens

VERSION = '2.0.0'
DIMENSIONS = ('completeness', 'cleanliness', 'structure', 'title', 'format')

def _bucket(value):
    return 4 if value >= .98 else 3 if value >= .90 else 2 if value >= .70 else 1 if value >= .40 else 0

def _identity(block):
    # Whitespace is ignored for alignment only; code whitespace is checked
    # separately by format. DOM ids do not determine content identity.
    return ' '.join(block['text'].split())

def _attributes(block):
    kind = block['kind']
    fields = {'kind': kind}
    if kind == 'heading': fields['heading_level'] = block.get('heading_level')
    if kind == 'list_item':
        fields.update({k: block.get(k, 0 if k == 'depth' else None)
                       for k in ('list_type', 'depth', 'ordinal')})
    if kind == 'footnote': fields['footnote_label'] = block.get('footnote_label')
    return fields

def _document(doc, name):
    if not isinstance(doc, dict): raise ValueError(f'{name} must be an object')
    if 'title' in doc and not isinstance(doc['title'], str):
        raise ValueError(f'{name}.title must be text')
    if 'blocks' not in doc: return None
    if not isinstance(doc['blocks'], list): raise ValueError(f'{name}.blocks must be a list')
    if len(doc['blocks']) > 2000: raise ValueError('At most 2000 blocks per document')
    for b in doc['blocks']:
        if not isinstance(b, dict) or not isinstance(b.get('text'), str) or not isinstance(b.get('kind'), str):
            raise ValueError('Each block needs text and kind strings')
    return doc['blocks']

def _alignment(predicted, gold):
    available = defaultdict(deque)
    for j, b in enumerate(gold): available[_identity(b)].append(j)
    pairs, unmatched = [], []
    for i, b in enumerate(predicted):
        key = _identity(b)
        if available[key]: pairs.append((i, available[key].popleft()))
        else: unmatched.append(i)
    missing = sorted(j for indices in available.values() for j in indices)
    return pairs, unmatched, missing

def _lis_length(indices):
    from bisect import bisect_left
    tails = []
    for index in indices:
        position = bisect_left(tails, index)
        if position == len(tails): tails.append(index)
        else: tails[position] = index
    return len(tails)

def score(predicted, gold=None, *, noise_terms=(), evidence_complete=True):
    """Score explicit gold only; missing/partial evidence requires review.

    Block positions in evidence are zero based p:N/g:N. Severity is a fixed
    diagnostic rule, not a calibrated semantic judgement or training reward.
    """
    pb = _document(predicted, 'predicted')
    if pb is None: raise ValueError('predicted.blocks is required')
    gb = _document(gold, 'gold') if gold is not None else None
    if type(evidence_complete) is not bool: raise ValueError('evidence_complete must be boolean')
    if not isinstance(noise_terms, (list, tuple)) or any(not isinstance(t, str) or not t.strip() for t in noise_terms):
        raise ValueError('noise_terms must contain nonempty strings')
    dimensions = {name: {'score': None, 'status': 'unscored', 'reason': 'No applicable reference annotation'} for name in DIMENSIONS}
    issues = []
    def issue(dimension, code, severity, p=None, g=None, detail=None):
        row = {'dimension': dimension, 'code': code, 'severity': severity,
               'predicted_ref': f'p:{p}' if p is not None else None,
               'gold_ref': f'g:{g}' if g is not None else None, 'detail': detail}
        if p is not None: row['predicted_excerpt'] = pb[p]['text'][:200]
        if g is not None: row['gold_excerpt'] = gb[g]['text'][:200]
        issues.append(row)
    if not pb: issue('completeness', 'empty_candidate', 'critical')
    if gb is not None:
        p = Counter(t for b in pb for t in _tokens(b['text']))
        g = Counter(t for b in gb for t in _tokens(b['text']))
        matched = sum((p & g).values())
        recall = matched / sum(g.values()) if g else 1.0
        precision = matched / sum(p.values()) if p else (1.0 if not g else 0.0)
        dimensions['completeness'] = {'score': _bucket(recall), 'status': 'scored', 'recall': recall, 'missing_tokens': sum((g-p).values())}
        text, expected = '\n'.join(b['text'] for b in pb), '\n'.join(b['text'] for b in gb)
        hits = {term: max(0, text.casefold().count(term) - expected.casefold().count(term))
                for term in sorted({t.casefold() for t in noise_terms})}
        ratio = max(0.0, precision - sum(hits.values()) * .25)
        dimensions['cleanliness'] = {'score': _bucket(ratio), 'status': 'scored', 'precision': precision,
                                     'clean_ratio': ratio, 'extra_tokens': sum((p-g).values()), 'noise_hits': hits}
        pairs, extra, missing = _alignment(pb, gb)
        for j in missing: issue('completeness', 'unaligned_gold_block', 'major' if recall < .7 else 'minor', g=j, detail='Exact normalized text not aligned; may be omission, edit or split/merge')
        for i in extra: issue('cleanliness', 'unaligned_candidate_block', 'major' if precision < .7 else 'minor', p=i, detail='Exact normalized text not aligned; may be extra text, edit or split/merge')
        for term, count in hits.items():
            if count: issue('cleanliness', 'explicit_noise_term', 'major', detail={'term':term, 'excess_count':count,
                'candidate_refs':[f'p:{i}' for i,b in enumerate(pb) if term in b['text'].casefold()]})
        attribute_ok = 0
        for i, j in pairs:
            if _attributes(pb[i]) == _attributes(gb[j]): attribute_ok += 1
            else: issue('structure', 'attribute_mismatch', 'major', i, j, {'predicted':_attributes(pb[i]), 'gold':_attributes(gb[j])})
        ordered = _lis_length([j for _, j in pairs])
        if ordered < len(pairs): issue('structure', 'block_order_mismatch', 'major', detail={'aligned_order':[j for _,j in pairs]})
        if pairs:
            attribute_ratio = attribute_ok / len(pairs)
            order_ratio = ordered / len(pairs)
            value = min(attribute_ratio, order_ratio)
            dimensions['structure'] = {'score': _bucket(value), 'status':'partial' if extra or missing else 'scored',
                'attribute_ratio':attribute_ratio, 'order_ratio':order_ratio, 'alignment_coverage':2*len(pairs)/(len(pb)+len(gb)),
                'aligned_pairs':[[i,j] for i,j in pairs], 'reason':'Only text-aligned blocks are scored' if extra or missing else None}
        else:
            dimensions['structure']['reason'] = 'No aligned blocks; structural quality is unknown'
        code_pairs = [(i,j) for i,j in pairs if gb[j]['kind']=='code' or pb[i]['kind']=='code']
        expected_codes = sum(b['kind']=='code' for b in gb)
        predicted_codes = sum(b['kind']=='code' for b in pb)
        if code_pairs:
            correct = 0
            for i,j in code_pairs:
                if pb[i]['text']==gb[j]['text'] and pb[i]['kind']==gb[j]['kind']=='code': correct += 1
                else: issue('format', 'code_format_mismatch', 'major', i, j, 'Code text/whitespace or block kind differs')
            value = correct / len(code_pairs)
            dimensions['format'] = {'score':_bucket(value), 'status':'scored' if len(code_pairs)==expected_codes==predicted_codes else 'partial',
                                     'code_exact_ratio':value, 'code_pairs_checked':len(code_pairs), 'scope':'Aligned code blocks only; Markdown render and links are unassessed'}
        else:
            dimensions['format'].update(reason='No code blocks to compare' if not expected_codes and not predicted_codes else 'No aligned code blocks', status='not_applicable' if not expected_codes and not predicted_codes else 'unscored')
    if gold is not None and 'title' in gold:
        expected_title, actual_title = ' '.join(gold['title'].split()), ' '.join(predicted.get('title','').split())
        value = 4 if actual_title == expected_title else (3 if actual_title and re.sub(r'^\d+(?:\.\d+)*[.、]?\s*', '', expected_title)==actual_title else 0)
        dimensions['title'] = {'score':value,'status':'scored','exact':actual_title==expected_title}
        if value < 4: issue('title','title_mismatch','minor' if value==3 else 'major',detail={'predicted':actual_title,'gold':expected_title})
    if not evidence_complete:
        for dimension in dimensions.values():
            if dimension['score'] is not None: dimension['status']='partial'
        issue('completeness','partial_source_evidence','unknown',detail='Scores cover supplied evidence only')
    unresolved = any(d['status'] in ('partial','unscored') for d in dimensions.values())
    major = any(i['severity'] in ('major','critical') for i in issues)
    # Averages cannot override an unresolved dimension or a serious error.
    verdict = 'fail' if major else 'uncertain' if unresolved or issues else 'pass'
    return {'rubrics_version':VERSION,'method':'deterministic-reference','dimensions':dimensions,'issues':issues,
            'decision':verdict,'needs_human_review':bool(issues) or unresolved,
            'overall':None,'evidence_complete':evidence_complete,
            'note':'Uncalibrated diagnostics; no model/human judgement or reward claim. Source attribution, links and Markdown rendering are unassessed.'}
