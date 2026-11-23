"""Author P-D2 controlled synthetic drift fixtures (id-drift, section-drift).

Never runs an extractor; never touches the original five drift_lab fixtures.
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


def article_body(tag='div', attrs=''):
    return (f'<{tag}{attrs}><h1>{TITLE}</h1>'
            + ''.join(f'<p>{value}</p>' for value in PARAGRAPHS) + f'</{tag}>')


def main():
    expected = {
        'title': TITLE,
        'paragraphs': PARAGRAPHS,
        'blocks': [dict(kind='paragraph', text=value, list_type=None,
                        depth=0, ordinal=None) for value in PARAGRAPHS],
        'annotation_note': ('Synthetic controlled mutation. Preserve all three article '
                            'sentences once. Exclude navigation/footer and duplicate '
                            'responsive rendering. No real-site validation claim.'),
    }
    reference_hash = digest((ROOT / 'reference.html').read_bytes())
    variants = [
        ('id-drift', document(article_body(attrs=' id="article-body" class="article-shell-v3"')),
         'id-article-body-div', 'rule_no_match',
         'The container loses the role attribute and is identified only by id="article-body"; '
         'tag layout is unchanged from reference. Prose is unchanged.'),
        ('section-drift', document(article_body(tag='section', attrs=' class="article-shell-v4"')),
         'section-v4', 'rule_no_match',
         'The container tag changes from div to section with a new class; no role or id. '
         'Tag-path fingerprint changes. Prose is unchanged.'),
    ]
    records = []
    for stem, source, layout, status, mutation in variants:
        html_name = stem + '.html'
        expected_name = stem + '.expected.json'
        html_hash = store(html_name, source)
        expected_hash = store(expected_name, serialized(expected))
        record = dict(id=stem, source_kind='synthetic', split='controlled_drift',
                      generator='build_fixtures_v2.py', html=html_name,
                      sha256=html_hash, expected=expected_name,
                      expected_sha256=expected_hash, layout=layout,
                      reference_html='reference.html', reference_sha256=reference_hash,
                      mutation=mutation, expected_status=status, expected_blocks_exact=None,
                      annotation_method='Authored three-sentence gold before extraction; '
                                        'no production imports or predictions used.')
        store(html_name + '.source.json', serialized(record))
        records.append(record)
    print(json.dumps({'new_cases': len(records), 'root': str(ROOT),
                      'hashes': {r['id']: r['sha256'] for r in records}}))


if __name__ == '__main__':
    main()
