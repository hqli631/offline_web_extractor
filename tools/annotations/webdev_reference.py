"""Independent source transcription for one web.dev course-overview snapshot.

Source DOM reviewed before prediction. This is page-specific annotation code;
it neither imports production code nor inspects extraction results.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from lxml import html

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'samples/webdev-learn-html.candidate.html'
OUTPUT = ROOT / 'samples/webdev-learn-html.candidate.expected.json'
SOURCE_SHA256 = '921c15fafe14485c9891ea1ad6bac7f42779fd57ed71fabd34c82b66c9664cee'


def normalized(node):
    return ' '.join(''.join(node.itertext()).split())


def block(kind, text, **metadata):
    return dict(kind=kind, text=text, list_type=None, depth=0, ordinal=None, **metadata)


def transcribe():
    raw = SOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA256
    # The saved document is UTF-8; avoid lxml's encoding guess for raw bytes.
    document = html.fromstring(raw.decode('utf-8'))
    playlists = document.xpath('//main//devsite-playlist')
    assert len(playlists) == 1
    playlist = playlists[0]
    assert len(playlist) == 3
    assert playlist[0].get('class') == 'devsite-playlist--header'
    titles = playlist[0].xpath('.//h1')
    assert len(titles) == 1 and normalized(titles[0]) == 'Learn HTML'
    intro_nodes = playlist[0].xpath('.//p')
    assert len(intro_nodes) == 1
    intro = deepcopy(intro_nodes[0])
    controls = intro.xpath('./a[@hidden]')
    assert len(controls) == 1 and normalized(controls[0]) == 'Go back'
    controls[0].drop_tree()
    introduction = normalized(intro)
    paragraphs = [introduction]
    blocks = [block('paragraph', introduction)]
    sections = playlist[1].xpath('./div/div')
    assert len(sections) == 23
    for index, section in enumerate(sections):
        if index == 22:
            assert section.get('type') == 'quiz'
            assert normalized(section.xpath('.//h2')[0]) == 'Quiz'
            continue  # Badge/completion interaction, not course subject content.
        assert section.get('type') == 'article'
        headings = section.xpath('.//h2')
        summaries = section.xpath('.//p')
        assert len(headings) == len(summaries) == 1
        blocks.append(block('heading', normalized(headings[0]), heading_level=2))
        summary = normalized(summaries[0])
        paragraphs.append(summary)
        blocks.append(block('paragraph', summary))
    assert len(blocks) == 45 and len(paragraphs) == 23
    assert blocks[-2]['text'] == 'Conclusion and next steps'
    assert blocks[-1]['text'] == 'Wrapping up with some further resources.'
    assert paragraphs[0] == paragraphs[1], 'Welcome summary is repeated in source and intentionally retained.'
    return dict(title='Learn HTML', paragraphs=paragraphs, blocks=blocks)


if __name__ == '__main__':
    expected = transcribe()
    serialized = json.dumps(expected, ensure_ascii=False, indent=2) + '\n'
    if OUTPUT.exists():
        assert OUTPUT.read_text(encoding='utf-8') == serialized, 'Frozen annotation differs; create a reviewed new version.'
    else:
        OUTPUT.write_text(serialized, encoding='utf-8')
    print(json.dumps(dict(blocks=len(expected['blocks']), paragraphs=len(expected['paragraphs']),
                         sha256=hashlib.sha256(OUTPUT.read_bytes()).hexdigest())))
