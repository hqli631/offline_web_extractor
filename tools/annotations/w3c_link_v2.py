"""Independent source-based quote-kind migration; never imports production code.

Only five reviewed blockquote/p nodes change metadata. Frozen v1 and its first
report are read only for checksums; no prediction informs scope or the new gold.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from lxml import html


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'samples/w3c-link-text.candidate.html'
OLD = ROOT / 'samples/w3c-link-text.candidate.expected.json'
NEW = ROOT / 'samples/w3c-link-text.candidate.expected.v2.json'
REVISION = ROOT / 'samples/annotation_revision.quote_v2.json'
PROTOCOL = ROOT / 'docs/ANNOTATION_PROTOCOL_v1.2.md'
FIRST = ROOT / 'outputs/w3c-link-text.candidate.first_evaluation.json'
SOURCE_HASH = '455f237d8b95ab058c974a660c10027fe65b79747beee872d4b6d987884527b5'
OLD_HASH = 'ebaae88d7af06eeabd4bef5ef752c42ef45eae01e3b12a5716e6f26c19b40d16'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert digest(SOURCE) == SOURCE_HASH
    assert digest(OLD) == OLD_HASH
    first_hash = digest(FIRST)
    reference = json.loads(OLD.read_text(encoding='utf-8'))
    migrated = deepcopy(reference)
    document = html.fromstring(SOURCE.read_bytes())
    nodes = document.xpath('//div[@id="main"]/blockquote/p')
    assert len(nodes) == 5
    changes = []
    for node in nodes:
        text = ' '.join(''.join(node.itertext()).split())
        indexes = [i for i, block in enumerate(reference['blocks'])
                   if block['text'] == text]
        assert len(indexes) == 1, 'Review repeated quote text explicitly'
        index = indexes[0]
        assert reference['blocks'][index]['kind'] == 'paragraph'
        migrated['blocks'][index]['kind'] = 'quote'
        changes.append(dict(block_index=index,
                            source_xpath=node.getroottree().getpath(node),
                            old_kind='paragraph', new_kind='quote', text=text))
    assert [c['block_index'] for c in changes] == [8, 10, 12, 14, 16]
    assert reference['title'] == migrated['title']
    assert reference['paragraphs'] == migrated['paragraphs']
    assert len(reference['blocks']) == len(migrated['blocks']) == 22
    assert [b['text'] for b in reference['blocks']] == [b['text'] for b in migrated['blocks']]
    for old, new in zip(reference['blocks'], migrated['blocks']):
        assert {k: v for k, v in old.items() if k != 'kind'} == {
            k: v for k, v in new.items() if k != 'kind'}
    serialized = json.dumps(migrated, ensure_ascii=False, indent=2) + '\n'
    if NEW.exists():
        assert NEW.read_text(encoding='utf-8') == serialized
    else:
        with NEW.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(serialized)
    revision = dict(
        created_at=datetime.now(timezone.utc).isoformat(),
        reason='Unify blockquote paragraph structure across source-reviewed pages, not a content correction and not a change to fit production predictions.',
        protocol='docs/ANNOTATION_PROTOCOL_v1.2.md',
        protocol_sha256=digest(PROTOCOL),
        source='samples/w3c-link-text.candidate.html', source_sha256=SOURCE_HASH,
        old_expected='samples/w3c-link-text.candidate.expected.json', old_sha256=OLD_HASH,
        new_expected='samples/w3c-link-text.candidate.expected.v2.json', new_sha256=digest(NEW),
        first_report='outputs/w3c-link-text.candidate.first_evaluation.json',
        preserved_first_report_sha256=first_hash,
        changes=changes,
        invariants=dict(text_order_unchanged=True, paragraphs_unchanged=True,
                        other_metadata_unchanged=True, old_files_preserved=True),
        baseline_selection=dict(
            w3c_link_text='samples/w3c-link-text.candidate.expected.v2.json',
            github_copilot='samples/github-copilot-blog.candidate.expected.json',
            note='GitHub existing quote already follows v1.2; no new prediction was run. Historical first metrics retain v1 references.'),
        review='Assistant independent DOM review, not user-by-user verified; no production imports or prediction content read.')
    if REVISION.exists():
        old_revision = json.loads(REVISION.read_text(encoding='utf-8'))
        for key in ['old_sha256', 'new_sha256', 'protocol_sha256', 'changes',
                    'preserved_first_report_sha256']:
            assert old_revision[key] == revision[key]
    else:
        with REVISION.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(revision, ensure_ascii=False, indent=2) + '\n')
    assert digest(OLD) == OLD_HASH
    assert digest(FIRST) == first_hash
    print(json.dumps(dict(blocks=len(migrated['blocks']),
                          kinds=dict(Counter(b['kind'] for b in migrated['blocks'])),
                          changed_indexes=[c['block_index'] for c in changes],
                          old_sha256=OLD_HASH, new_sha256=digest(NEW)), indent=2))


if __name__ == '__main__':
    main()
