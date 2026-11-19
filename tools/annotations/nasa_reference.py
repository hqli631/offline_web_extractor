"""DOM-assisted reference transcription for the frozen NASA snapshot.

This is an annotation artifact, not a production extractor: source children were
read and selected before viewing any prediction. It imports no project code.
The original frozen expected is never overwritten.
"""

import hashlib
import json
from pathlib import Path

from lxml import html


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'samples/nasa-voyager-news.candidate.html'
EXPECTED = ROOT / 'samples/nasa-voyager-news.candidate.expected.json'
SOURCE_HASH = 'e7f443d226454244fd9c4a6532a1de1697c7463d69aadac8751c1ab396510e22'


def normalized(node):
    return ' '.join(''.join(node.itertext()).split())


def main():
    payload = SOURCE.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == SOURCE_HASH
    document = html.fromstring(payload)
    title_nodes = document.xpath('//main/article//h1')
    assert len(title_nodes) == 1
    title = normalized(title_nodes[0])
    assert title == 'NASA Invites Media, Public to Join Voyager 1 One-Light Day Activities'
    body_nodes = document.xpath("//div[contains(concat(' ',normalize-space(@class),' '),' entry-content ')]")
    assert len(body_nodes) == 1
    children = list(body_nodes[0])
    assert len(children) == 20
    # Source children 1..16 are the news text and participant list.
    # 0 is a figure/caption; 17 is '-end-'; 18..19 are press contacts.
    assert normalized(children[17]) == '-end-'
    paragraphs = []
    blocks = []
    for index in range(1, 17):
        node = children[index]
        if index == 9:
            assert node.tag == 'ul'
            items = node.xpath('./li')
            assert len(items) == 5
            for item in items:
                blocks.append(dict(kind='list_item', text=normalized(item),
                                   list_type='ul', depth=0, ordinal=None))
        else:
            assert node.tag == 'p'
            text = normalized(node)
            paragraphs.append(text)
            blocks.append(dict(kind='paragraph', text=text, list_type=None,
                               depth=0, ordinal=None))
    assert paragraphs[0].startswith('Launched nearly 50 years ago in 1977,')
    assert paragraphs[-1] == 'https://science.nasa.gov/mission/voyager/'
    expected = dict(title=title, paragraphs=paragraphs, blocks=blocks)
    serialized = json.dumps(expected, ensure_ascii=False, indent=2) + '\n'
    if EXPECTED.exists():
        assert EXPECTED.read_text(encoding='utf-8') == serialized, 'Frozen annotation differs; create a reviewed new version.'
    else:
        EXPECTED.write_text(serialized, encoding='utf-8')
    print(json.dumps(dict(blocks=len(blocks), paragraphs=len(paragraphs),
                         sha256=hashlib.sha256(EXPECTED.read_bytes()).hexdigest())))


if __name__ == '__main__':
    main()
