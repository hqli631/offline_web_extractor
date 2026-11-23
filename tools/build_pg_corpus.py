# -*- coding: utf-8 -*-
"""P-G G2 corpus builder: controlled drift variants + mixed 28-page manifest.

For each collected family, builds ONE controlled drift variant from the family
representative (first accepted page): swap the content container tag
(div<->section, article/main->div) and strip its role/id attributes, preserving
all prose verbatim. Silver expected = representative extract_html blocks
(PROGRAMMATIC silver, NOT human gold; disclosed). The mutation breaks every
derive_shared_rule selector (role/main/article/div.body) and changes tag-path
fingerprints, guaranteeing drift triggers. Verifies paragraph-text multiset
preservation and records rule-before / rule-status-after feasibility. Existing
13 development snapshots are included byte-identical as mixed-corpus distractors
(clustering/reuse only; no critic/repair). Refuses overwrite. Zero network/calls.
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from lxml import html

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.webextractor.extractor import extract_html, normalize_text
from src.webextractor.rule_cache import derive_shared_rule, apply_rule

TOOL_VERSION = '1.0.0'
EXISTING_MANIFEST = 'samples/dom_similarity.expanded_development.json'
TAG_SWAP = {'div': 'section', 'section': 'div', 'article': 'div', 'main': 'div'}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def _paragraph_texts(source):
    tree = html.fromstring(source, parser=html.HTMLParser(no_network=True))
    return Counter(normalize_text(p) for p in tree.xpath('//p'))


def build_variant(rep_source, variant_id):
    """Return variant payload dict or None if container not locatable."""
    res = extract_html(rep_source)
    if res.selected_candidate is None:
        return None
    tree = html.fromstring(rep_source, parser=html.HTMLParser(no_network=True))
    elems = tree.xpath(res.selected_candidate.xpath)
    if len(elems) != 1:
        return None
    el = elems[0]
    old_tag = el.tag if isinstance(el.tag, str) else None
    if old_tag is None:
        return None
    new_tag = TAG_SWAP.get(old_tag, 'section')
    before_paragraphs = _paragraph_texts(rep_source)
    el.tag = new_tag
    el.attrib.pop('role', None)
    el.attrib.pop('id', None)
    mutated = html.tostring(tree, encoding='unicode', doctype='<!doctype html>')
    if _paragraph_texts(mutated) != before_paragraphs:
        return None
    rule_before = derive_shared_rule(rep_source)
    rule_after = apply_rule(mutated.encode('utf-8'), rule_before) if rule_before else None
    silver = {'title': res.title, 'blocks': res.to_dict()['blocks'],
              'annotation_note': ('PROGRAMMATIC silver expected = representative extract_html blocks. '
                                  'NOT human gold. Used only for orchestrator-side recall side-check and '
                                  'feedback validation; never enters any model prompt.')}
    return {'variant_id': variant_id, 'html': mutated, 'silver': silver,
            'mutation': {'old_tag': old_tag, 'new_tag': new_tag, 'stripped_attrs': ['role', 'id'],
                         'container_xpath': res.selected_candidate.xpath,
                         'prose_preserved': True},
            'rule_before': rule_before,
            'rule_status_after': rule_after['status'] if rule_after else 'no_rule_before',
            'rule_broken': (rule_after is None) or rule_after['status'] != 'ok' or rule_after['block_count'] == 0}


def build_corpus(collect_path, manifest_path, samples_root=None, include_existing=True):
    collect_path, manifest_path = Path(collect_path), Path(manifest_path)
    if manifest_path.exists():
        raise FileExistsError('refusing to overwrite existing corpus manifest')
    collect = json.loads(collect_path.read_text(encoding='utf-8'))
    accepted = collect['accepted_pages']
    samples = Path(samples_root) if samples_root else ROOT / 'samples'
    pg_dir = samples / 'pg_v1'
    families = {}
    for a in accepted:
        families.setdefault(a['family'], []).append(a)
    pages, variant_records, family_info = [], [], {}
    for fam, members in families.items():
        rep = members[0]
        rep_source = (samples / rep['html']).read_bytes()
        vid = rep['page_id'] + '-var'
        v = build_variant(rep_source, vid)
        family_info[fam] = {'rep_id': rep['page_id'], 'members': [m['page_id'] for m in members],
                            'variant_id': vid if v else None,
                            'variant_feasible': v is not None,
                            'variant_rule_broken': v['rule_broken'] if v else None}
        if v is not None:
            hp = pg_dir / (vid + '.html')
            ep = pg_dir / (vid + '.expected.json')
            sp = pg_dir / (vid + '.html.source.json')
            for p in (hp, ep, sp):
                if p.exists():
                    raise FileExistsError('refusing to overwrite ' + str(p))
            hb = v['html'].encode('utf-8')
            eb = (json.dumps(v['silver'], ensure_ascii=False, indent=2) + '\n').encode('utf-8')
            hp.write_bytes(hb)
            ep.write_bytes(eb)
            record = {'id': vid, 'source_kind': 'synthetic_variant', 'split': 'development',
                      'generator': 'build_pg_corpus.py', 'html': 'pg_v1/' + hp.name,
                      'sha256': sha(hb), 'expected': 'pg_v1/' + ep.name, 'expected_sha256': sha(eb),
                      'rep_html': rep['html'], 'rep_sha256': rep['sha256'],
                      'mutation': v['mutation'], 'rule_before': v['rule_before'],
                      'rule_status_after': v['rule_status_after'], 'rule_broken': v['rule_broken'],
                      'silver_method': 'representative extract_html blocks (programmatic silver, NOT human gold)',
                      'fetched_at': collect['generated_at']}
            sp.write_bytes((json.dumps(record, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
            variant_records.append(record)
            pages.append({'id': vid, 'html': 'pg_v1/' + hp.name, 'sha256': sha(hb),
                          'manual_group': fam, 'source_kind': 'synthetic_variant', 'split': 'development',
                          'layout': 'tag-swap-role-stripped', 'silver_expected': 'pg_v1/' + ep.name,
                          'rep_id': rep['page_id']})
    for a in accepted:
        pages.append({'id': a['page_id'], 'html': a['html'], 'sha256': a['sha256'],
                      'manual_group': a['family'], 'source_kind': 'real_new', 'split': 'development',
                      'layout': 'natural', 'exposed': a['exposed'], 'url': a['url']})
    existing_ids = []
    if include_existing:
        existing = json.loads((ROOT / EXISTING_MANIFEST).read_text(encoding='utf-8'))
        for p in existing['pages']:
            sb = (samples / p['html']).read_bytes()
            pages.append({'id': p['id'], 'html': p['html'], 'sha256': sha(sb),
                          'manual_group': p['manual_group'], 'source_kind': 'real_existing',
                          'split': 'development', 'layout': 'existing'})
            existing_ids.append(p['id'])
    new_ids = [p['id'] for p in pages if p['source_kind'] in ('real_new', 'synthetic_variant')]
    manifest = {'protocol': ('P-G mixed real corpus: newly collected unexposed template families + '
                             'one controlled tag-swap/role-strip drift variant per family (silver expected = '
                             'rep extract_html blocks, NOT gold) + 13 existing development snapshots '
                             '(byte-identical distractors, clustering/reuse only). suffix-presence protocol '
                             'adoption validated here per docs/P_G_REAL_TEMPLATE_PLAN.md.'),
                'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'collect_log_sha256': sha(collect_path.read_bytes()),
                'strata': {'new': sorted(new_ids), 'existing': sorted(existing_ids),
                           'all': sorted(p['id'] for p in pages)},
                'families': family_info, 'variants': variant_records, 'pages': pages}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='')
    return manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description='P-G G2 corpus builder (zero calls/network).')
    ap.add_argument('--collect', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args(argv)
    if args.output.exists():
        print('Output exists; choose a new filename.', file=sys.stderr)
        return 3
    manifest = build_corpus(args.collect, args.output)
    print(json.dumps({'output': str(args.output), 'pages': len(manifest['pages']),
                      'strata': {k: len(v) for k, v in manifest['strata'].items()},
                      'families': manifest['families']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
