"""Independent DOM-assisted transcription of the reviewed W3C QA tip.

Page-specific source positions are deliberate annotation decisions. This script
does not import production extraction code or read prediction files.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from lxml import html

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'samples/w3c-link-text.candidate.html'
EXPECTED = ROOT / 'samples/w3c-link-text.candidate.expected.json'
SOURCE_SHA256 = '455f237d8b95ab058c974a660c10027fe65b79747beee872d4b6d987884527b5'


def normalized(node):
    return ' '.join(''.join(node.itertext()).split())


def block(kind, text, **metadata):
    return dict(kind=kind, text=text, list_type=None, depth=0, ordinal=None, **metadata)


def transcribe():
    raw = SOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA256
    document = html.fromstring(raw)
    mains = document.xpath('//div[@id="main"]')
    assert len(mains) == 1
    children = list(mains[0])
    assert len(children) == 21
    assert children[0].tag == 'h2'
    title = normalized(children[0])
    assert title == '''Don't use "click here" as link text'''
    assert children[17].get('id') == 'abouttips'
    blocks, paragraphs = [], []
    # Children 1..16 are the three advice sections. 17..20 are shared series
    # information (About QA Tips, disclaimer, index/submission promotion).
    for position in range(1, 17):
        node = children[position]
        if node.tag == 'h3':
            blocks.append(block('heading', normalized(node), heading_level=3))
        elif node.tag == 'p':
            value = normalized(node)
            paragraphs.append(value)
            blocks.append(block('paragraph', value))
        elif node.tag == 'blockquote':
            # v1.1 has no quote-wrapper block: preserve the actual nested p
            # text and order. Record quote styling as outside this protocol.
            assert len(node) == 1 and node[0].tag == 'p'
            value = normalized(node[0])
            paragraphs.append(value)
            blocks.append(block('paragraph', value))
        elif node.tag == 'ul':
            assert len(node) == 4 and all(child.tag == 'li' for child in node)
            for item in node:
                value = block('list_item', normalized(item))
                value['list_type'] = 'ul'
                blocks.append(value)
        else:
            raise AssertionError(f'Unreviewed source child {position}: {node.tag}')
    assert len(paragraphs) == 11 and len(blocks) == 22
    assert blocks[-1]['text'] == 'Mail thread on the www-qa list, suggesting this tip.'
    return dict(title=title, paragraphs=paragraphs, blocks=blocks)


if __name__ == '__main__':
    reference = transcribe()
    serialized = json.dumps(reference, ensure_ascii=False, indent=2) + '\n'
    if EXPECTED.exists():
        assert EXPECTED.read_text(encoding='utf-8') == serialized, 'Frozen reference differs; review a new version.'
    else:
        with EXPECTED.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(serialized)
    print(json.dumps(dict(blocks=len(reference['blocks']),
                         paragraphs=len(reference['paragraphs']),
                         expected_sha256=hashlib.sha256(EXPECTED.read_bytes()).hexdigest())))
