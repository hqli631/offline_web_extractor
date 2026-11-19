# -*- coding: utf-8 -*-
"""Shared synthetic fixtures for P0 human-review tool tests (no real data)."""
import json
from pathlib import Path

from tools.score_judge_results import DIMS, sha256_bytes, sha256_json


def _judge_dims():
    d = {n: {'score': 4, 'status': 'scored', 'severity': 'none',
             'reason': 'JUDGE_REASON_SENTINEL',
             'evidence': [{'ref': 's:0', 'quote': 'source text'}]} for n in DIMS}
    d['format'] = {'score': None, 'status': 'not_applicable', 'severity': 'none',
                   'reason': 'JUDGE_REASON_SENTINEL', 'evidence': []}
    d['structure'] = {'score': 3, 'status': 'scored', 'severity': 'minor',
                      'reason': 'JUDGE_REASON_SENTINEL',
                      'evidence': [{'ref': 's:0', 'quote': 'source text'}]}
    return d


def _silver_dims(struct_severity='major'):
    d = {n: {'score': 4, 'status': 'scored', 'severity': 'none'} for n in DIMS}
    d['format'] = {'score': None, 'status': 'not_applicable', 'severity': 'none'}
    d['structure'] = {'score': 3, 'status': 'scored', 'severity': struct_severity}
    return d


def _write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=1),
                          encoding='utf-8', newline='')


def make_fixture(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    manifest = {'judge_manifest_version': 1,
                'cases': [{'case_id': 'c1', 'split': 'development'},
                          {'case_id': 'c2', 'split': 'frozen_test'}]}
    mpath = root / 'manifest.json'
    _write_json(mpath, manifest)
    mb = mpath.read_bytes()
    cfg = {'model': 'test-model', 'max_source_chars': 20000,
           'max_output_tokens': 4096, 'timeout_seconds': 90}
    freeze = {'files': {'samples/calibration_manifest.json': sha256_bytes(mb)},
              'manifest_sha256': sha256_json(manifest),
              'cases': [
                  {'case_id': 'c1', 'candidate_sha256': 'aa',
                   'source_sha256': 'bb', 'gold_sha256': 'cc'},
                  {'case_id': 'c2', 'candidate_sha256': 'dd',
                   'source_sha256': 'ee', 'gold_sha256': None}],
              'batch_config': cfg}
    source = {'html_ref': 's:html', 'html': '<html><body><p>source text</p></body></html>',
              'nodes': [{'ref': 's:0', 'xpath': '/html/body/p', 'tag': 'p',
                         'text': 'source text'}],
              'truncated': False}
    candidate = {'title_ref': 'p:title', 'title': 'Title', 'block_count': 1,
                 'blocks': [{'ref': 'p:0', 'kind': 'paragraph', 'text': 'candidate text',
                             'list_type': None, 'depth': 0, 'ordinal': None}]}
    gold = {'title_ref': 'g:title', 'title': 'Title', 'block_count': 1,
            'blocks': [{'ref': 'g:0', 'kind': 'paragraph', 'text': 'source text',
                        'list_type': None, 'depth': 0, 'ordinal': None}]}
    c1 = {'case_id': 'c1', 'template': 't1', 'split': 'development', 'status': 'accepted',
          'cache_hit': True, 'new_api_call': False,
          'case_meta': {'mode': 'with_gold', 'candidate_sha256': 'aa',
                        'source_sha256': 'bb', 'gold_sha256': 'cc',
                        'source_truncated': False},
          'report': {'status': 'accepted', 'mode': 'with_gold',
                     'assessment': {'schema_version': 1, 'dimensions': _judge_dims(),
                                    'decision': 'uncertain', 'needs_human_review': True,
                                    'scope': 'test'},
                     'program_assessment': {
                         'dimensions': {n: {'score': 4, 'status': 'scored'} for n in DIMS},
                         'decision': 'fail', 'issues': []},
                     'error': None,
                     'prompt': {'protocol': {}, 'source': source,
                                'candidate': candidate, 'gold': gold}}}
    c2 = {'case_id': 'c2', 'template': 't2', 'split': 'frozen_test', 'status': 'rejected',
          'cache_hit': True, 'new_api_call': False,
          'case_meta': {'mode': 'source_only', 'candidate_sha256': 'dd',
                        'source_sha256': 'ee', 'gold_sha256': None,
                        'source_truncated': False},
          'report': {'status': 'rejected', 'mode': 'source_only', 'assessment': None,
                     'error': {'type': 'ValueError', 'stage': 'validation',
                               'detail': 'Scoring needs source/reference evidence'},
                     'prompt': {'protocol': {}, 'source': source,
                                'candidate': candidate}}}
    batch = {'tool': 'test', 'manifest_sha256': sha256_bytes(mb),
             'signature': dict(cfg), 'cases': [c1, c2],
             'new_api_calls': 0, 'usage_new_calls_only': []}
    stability = {'cases': [{'case_id': 'c1'}], 'new_api_calls': 0,
                 'usage_new_calls_only': []}
    paths = {'batch': root / 'batch.json', 'stability': root / 'stability.json',
             'freeze': root / 'freeze.json', 'manifest': mpath,
             'labels': root / 'labels'}
    _write_json(paths['batch'], batch)
    _write_json(paths['stability'], stability)
    _write_json(paths['freeze'], freeze)
    paths['labels'].mkdir()
    _write_json(paths['labels'] / 'c1.label.json',
                {'label_version': 1, 'case_id': 'c1', 'label_origin': 'assistant_silver',
                 'human_reviewed': False, 'mutation': {'type': 'reorder', 'indices': [0, 1]},
                 'source_truncated': False,
                 'expected': {'dimensions': _silver_dims('major'), 'decision': 'fail',
                              'needs_human_review': True}})
    _write_json(paths['labels'] / 'c2.label.json',
                {'label_version': 1, 'case_id': 'c2', 'label_origin': 'assistant_silver',
                 'human_reviewed': False, 'mutation': {'type': 'clean'},
                 'source_truncated': False,
                 'expected': {'dimensions': _silver_dims('none'), 'decision': 'uncertain',
                              'needs_human_review': True}})
    kit = root / 'kit'
    kit.mkdir()
    _write_json(kit / 'sealed_mapping.json', {'B01': 'c1', 'B02': 'c2'})
    paths['kit'] = kit
    return {'paths': paths, 'batch': batch, 'freeze': freeze}


def human_doc(batch, stage='blind', decision_c1='fail', sev_c1='major', confirmed=False):
    cases = []
    for row in batch['cases']:
        dims = {n: {'score': 4, 'status': 'scored', 'severity': 'none', 'note': ''}
                for n in DIMS}
        dims['format'] = {'score': None, 'status': 'not_applicable',
                          'severity': 'none', 'note': ''}
        decision = 'uncertain'
        if row['case_id'] == 'c1':
            dims['structure'] = {'score': 3, 'status': 'scored', 'severity': sev_c1,
                                 'note': ''}
            decision = decision_c1
        e = {'case_id': row['case_id'], 'split': row['split'],
             'mode': row['case_meta']['mode'], 'decision': decision,
             'dimensions': dims, 'overall_note': ''}
        if stage == 'final':
            e['confirmed'] = confirmed
            e['adjudication_note'] = 'checked'
        cases.append(e)
    return {'label_version': 1, 'stage': stage, 'annotator': 'tester',
            'annotation_date': '2026-11-17', 'cases': cases}
