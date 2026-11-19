"""Independent DOM-assisted reference transcription for the frozen GitHub page.

Scope was reviewed against the original HTML before any prediction. This is
page-specific annotation tooling, not the production extractor. It deliberately
does not import src, use its cleanup rules, or render expected from predictions.
The annotator selected the summary, each direct article child, the informational
blockquote, and the malformed feature-list items explicitly. UTF-8 is fixed from
the HTTP source record; parser fallback must not corrupt curly quotes or emoji.

The output is assistant-reviewed and has not been individually confirmed by the
human learner. The script refuses to overwrite a frozen reference.
"""

from collections import Counter
import hashlib
import json
from pathlib import Path

from lxml import html

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'samples/github-copilot-blog.candidate.html'
OUTPUT = ROOT / 'samples/github-copilot-blog.candidate.expected.json'
SOURCE_SHA256 = 'c0cb2ed0cf8a6c40e9b87a10b13d07a0f9ee3cd02356159a1ebfd0a9a756ca8c'


def text(node):
    return ' '.join(''.join(node.itertext()).split())


def block(kind, value, **metadata):
    return dict(kind=kind, text=value, list_type=None, depth=0, ordinal=None, **metadata)


def main():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256
    root = html.fromstring(SOURCE.read_text(encoding='utf-8'))
    title = root.xpath("//main[@id='start-of-content']/header//h1")
    assert len(title) == 1
    assert text(title[0]) == 'GitHub Copilot is generally available to all developers'
    summary = root.xpath("//main[@id='start-of-content']/header//p")
    assert len(summary) == 1
    article = root.xpath("//section[contains(concat(' ', normalize-space(@class), ' '), ' post__content ')]")
    assert len(article) == 1
    children = list(article[0])
    # Scope review identifies children 0..16 as the body. Child 17 is Tags;
    # child 18 is the author biography, both outside the article's content scope.
    assert [n.tag for n in children] == [
        'p', 'p', 'p', 'p', 'blockquote', 'h2', 'p', 'p', 'aside',
        'p', 'p', 'p', 'h2', 'p', 'p', 'h2', 'p', 'section', 'div'
    ]
    assert 'Tags:' in text(children[17])
    assert 'Written by' in text(children[18])
    blocks = [block('paragraph', text(summary[0]))]
    paragraphs = [text(summary[0])]
    for index in range(17):
        node = children[index]
        if index == 11:
            # Linked advertising image has no visible article prose. No OCR.
            assert not text(node) and node.xpath('.//img')
        elif index == 4:
            # Informational pull-quote contains trial/pricing/eligibility details.
            assert node.tag == 'blockquote' and len(node.xpath('./p')) == 1
            paragraphs.append(text(node.xpath('./p')[0]))
            blocks.append(block('quote', text(node)))
        elif index == 8:
            # Original markup has orphan li elements and literal p fragments
            # '<' and 'ul>'. Keep the feature prose; omit corrupted tag debris.
            label = node.xpath('./p')[0]
            assert text(label) == 'GitHub Copilot enables developers to'
            assert [text(n) for n in node.xpath('./p')[1:]] == ['<', 'ul>']
            paragraphs.append(text(label))
            blocks.append(block('paragraph', text(label)))
            items = node.xpath('./li')
            assert len(items) == 3
            for item in items:
                value = block('list_item', text(item))
                value['list_type'] = 'ul'
                blocks.append(value)
        elif node.tag == 'h2':
            blocks.append(block('heading', text(node), heading_level=2))
        else:
            assert node.tag == 'p' and text(node)
            paragraphs.append(text(node))
            blocks.append(block('paragraph', text(node)))
    expected = dict(title=text(title[0]), paragraphs=paragraphs, blocks=blocks)
    assert len(blocks) == 20 and len(paragraphs) == 14
    assert '\ufffd' not in json.dumps(expected, ensure_ascii=False)
    serialized = json.dumps(expected, ensure_ascii=False, indent=2) + '\n'
    with OUTPUT.open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(serialized)
    print('blocks:', dict(Counter(b['kind'] for b in blocks)))
    print('paragraphs:', len(paragraphs))
    print('expected_sha256:', hashlib.sha256(OUTPUT.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
