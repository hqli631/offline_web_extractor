"""DOM-assisted transcription for one reviewed GNU snapshot, not an extractor.

This reference is authored from the raw HTML and the declared scope only.
It deliberately does not import production code or read any prediction.
Run before the first prediction; existing expected files are never overwritten.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

from lxml import html

PROJECT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT / 'samples/gnu.candidate.html'
OUTPUT = PROJECT / 'samples/gnu.candidate.expected.json'
SOURCE_SHA256 = 'b050aa1bcbf73c225c0bcabd377e1015a4c602556eb6d9f13f0eb2d5ba8973d6'


def text(node):
    return ' '.join(''.join(node.itertext()).split())


def block(kind, value, **metadata):
    return dict(kind=kind, text=value, list_type=None, depth=0, ordinal=None, **metadata)


def transcribe():
    raw = SOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA256
    document = html.fromstring(raw)
    articles = document.xpath(
        "//div[contains(concat(' ', normalize-space(@class), ' '), ' article ')"
        " and contains(concat(' ', normalize-space(@class), ' '), ' reduced-width ')]")
    assert len(articles) == 1
    article = articles[0]
    assert len(article) == 77, 'Snapshot layout changed; review before transcription'
    assert text(article[0]) == 'What is Free Software?'
    assert len(article.xpath('./dl/dt')) == len(article.xpath('./dl/dd')) == 27
    assert len(article.xpath('./dl/dd/ul/li')) == 4
    assert len(article.xpath('./ol/li')) == 1
    blocks, paragraphs = [], []
    # Explicit, page-specific scope reviewed against all direct children.
    for index, node in enumerate(article):
        if index in {0, 1, 5, 6, 74}:
            # Article title, empty decorative div, TOC, licensing consultation,
            # empty column-limit div. No whole-document noise heuristics.
            continue
        if index == 2:
            assert node.get('class') == 'important' and len(node) == 2
            for paragraph in node:
                assert paragraph.tag == 'p'
                paragraphs.append(text(paragraph))
                blocks.append(block('paragraph', text(paragraph)))
        elif node.tag == 'p':
            paragraphs.append(text(node))
            blocks.append(block('paragraph', text(node)))
        elif node.tag in {'h3', 'h4'}:
            blocks.append(block('heading', text(node), heading_level=int(node.tag[1])))
        elif index == 11:
            assert node.tag == 'ul' and len(node) == 4
            for item in node:
                entry = block('list_item', text(item))
                entry['list_type'] = 'ul'
                blocks.append(entry)
        elif index == 72:
            assert node.tag == 'dl'
            for entry in node:
                if entry.tag == 'dt':
                    blocks.append(block('definition_term', text(entry)))
                else:
                    assert entry.tag == 'dd'
                    nested = entry.xpath('./ul')
                    if not nested:
                        blocks.append(block('definition_description', text(entry)))
                    else:
                        assert len(entry) == 1 and len(nested) == 1
                        # Version 1.74 introductory description precedes four
                        # standalone unordered items. They are not part of the
                        # description string and are not nested in another list.
                        blocks.append(block('definition_description', ' '.join(entry.text.split())))
                        for item in nested[0]:
                            value = block('list_item', text(item))
                            value['list_type'] = 'ul'
                            blocks.append(value)
                        assert not nested[0].tail.strip()
        elif index == 76:
            assert node.tag == 'ol' and node[0].get('id') == 'f1'
            footnote = node[0]
            assert not footnote.xpath('.//a'), 'Review backlink controls if source changes'
            blocks.append(block('footnote', text(footnote), footnote_label='[1]', source_id='f1'))
        else:
            raise AssertionError(f'Unreviewed child: {index} {node.tag}')
    assert blocks[0]['text'].startswith('“Free software” means software')
    assert blocks[-1]['text'].endswith('Rather than renumber the others, we made it freedom 0.')
    assert len([b for b in blocks if b['kind'] == 'footnote']) == 1
    return dict(title='What is Free Software?', paragraphs=paragraphs, blocks=blocks)


if __name__ == '__main__':
    result = transcribe()
    # Exclusive creation protects frozen standards from accidental overwrite.
    with OUTPUT.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({
        'output': str(OUTPUT), 'blocks': len(result['blocks']),
        'paragraphs': len(result['paragraphs']),
        'kinds': dict(Counter(b['kind'] for b in result['blocks'])),
        'expected_sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    }, indent=2))
