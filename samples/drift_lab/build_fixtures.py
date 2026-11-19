"""Author controlled synthetic drift fixtures; never run an extractor.

Expected prose is fixed below independently of DOM traversal and production
code. Re-running verifies existing identical files, refusing changed artifacts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TITLE = "Template drift laboratory"
PARAGRAPHS = [
    "The reference article begins here.",
    "The second paragraph explains why a reusable rule needs stable structure.",
    "The closing paragraph is required even when its container changes.",
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def store(name, content):
    payload = content.encode('utf-8')
    path = ROOT / name
    if path.exists():
        assert path.read_bytes() == payload, f'Existing artifact differs: {name}'
    else:
        path.write_bytes(payload)
    return digest(payload)


def serialized(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def document(inner):
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<title>Controlled drift fixture</title></head><body>\n'
            '<nav><p>Site navigation: excluded from article.</p></nav>\n'
            + inner + '\n<footer><p>Site footer: excluded from article.</p></footer>'
            '\n</body></html>\n')


def article(role='main', css='article-shell', values=None):
    values = PARAGRAPHS if values is None else values
    return (f'<div role="{role}" class="{css}"><h1>{TITLE}</h1>'
            + ''.join(f'<p>{value}</p>' for value in values) + '</div>')


def main():
    # This gold is authored from the three intended sentences, not an extractor.
    expected = {
        'title': TITLE,
        'paragraphs': PARAGRAPHS,
        'blocks': [dict(kind='paragraph', text=value, list_type=None,
                        depth=0, ordinal=None) for value in PARAGRAPHS],
        'annotation_note': ('Synthetic controlled mutation. Preserve all three article '
                            'sentences once. Exclude navigation/footer and duplicate '
                            'responsive rendering. No real-site validation claim.'),
    }
    baseline = document(article())
    variants = [
        ('reference', baseline, 'reference', 'ok', True,
         'Authored synthetic reference, no mutation.'),
        ('class-drift', document(article(css='new-layout article-shell-v2')),
         'transfer', 'ok', True,
         'Only class value changes. The frozen role XPath remains applicable.'),
        ('role-drift', document(article(role='article')),
         'transfer', 'rule_no_match', None,
         'The role attribute changes from main to article; prose is unchanged.'),
        ('duplicate-main', document(article(css='desktop-layout') + '\n'
                                    + article(css='mobile-layout')),
         'transfer', 'rule_ambiguous', None,
         'Two responsive copies expose role=main. Intended article is the same '
         'three sentences once. The runner must reject ambiguity instead of picking one.'),
        ('content-moved', document(article(values=PARAGRAPHS[:2])
                                  + '<section class="article-continuation"><p>'
                                  + PARAGRAPHS[2] + '</p></section>'),
         'transfer', 'ok', False,
         'The closing paragraph moves into a sibling section outside the main div. '
         'Frozen XPath still matches exactly once, but extraction is incomplete.'),
    ]
    pages = []
    records = []
    reference_hash = digest(baseline.encode('utf-8'))
    for stem, source, role, status, exact, mutation in variants:
        html_name = stem + '.html'
        expected_name = stem + '.expected.json'
        html_hash = store(html_name, source)
        expected_hash = store(expected_name, serialized(expected))
        record = dict(id=stem, source_kind='synthetic', split='controlled_drift',
                      generator='build_fixtures.py', html=html_name,
                      sha256=html_hash, expected=expected_name,
                      expected_sha256=expected_hash,
                      reference_html='reference.html',
                      reference_sha256=reference_hash, mutation=mutation,
                      expected_status=status, expected_blocks_exact=exact,
                      annotation_method='Authored three-sentence gold before extraction; '
                                        'no production imports or predictions used.')
        store(html_name + '.source.json', serialized(record))
        pages.append(dict(id=stem, role=role, html=html_name, sha256=html_hash,
                          expected=expected_name, expected_sha256=expected_hash,
                          source_kind='synthetic', expected_status=status,
                          expected_blocks_exact=exact))
        records.append(record)
    store('reuse.json', serialized({
        'rule': dict(id='controlled-role-main-v1',
                     container_xpath="//div[@role='main']",
                     frozen_from='reference',
                     note='One frozen rule, no fallback or per-page adaptation. '
                          'All pages are authored synthetic controlled mutations.'),
        'pages': pages,
        'protocol': 'Expected status and quality fields are experiment assertions; '
                    'the current reuse runner may ignore them. Full-page gold is '
                    'distinct from container match applicability.',
    }))
    store('provenance.json', serialized({
        'source_kind': 'synthetic',
        'purpose': 'Controlled drift mechanisms, not fresh real-world generalization.',
        'reference_sha256': reference_hash,
        'rule_xpath': "//div[@role='main']",
        'cases': records,
    }))
    print(json.dumps({'cases': len(pages), 'root': str(ROOT),
                      'html_and_expected_hashes_verified': True}))


if __name__ == '__main__':
    main()
