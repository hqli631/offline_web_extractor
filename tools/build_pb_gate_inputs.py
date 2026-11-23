# -*- coding: utf-8 -*-
"""P-B zero-call gate input builder (step-4 branch: judge v1.2 retained).

Builds gate-compatible dev inputs for tools/score_p3_gate.py from SEALED
artifacts only, per docs/P_B_AMENDMENT_PROPOSAL.md (pre-registered):

  * dev batch views: p1_5.dev.v1.json (orig dev12, as-ran under v1.2) and
    p2.judge.v2.json filtered to its development split (P2 dev6). The P2
    batch also contains consumed frozen_test v2 cases which must NEVER be
    re-scored; filtering them out is mandatory for gate integrity.
  * dev gold overlays: sealed human gold + exactly the sealed adjudicated
    corrections (C01/C02 from P3 findings, A01 from P-A findings; all
    verdict=judge_correct). Sealed gold files are never modified.

Correction rule (pre-registered, minimal, auditable):
  verdict=judge_correct -> for each divergent dimension named in the sealed
  findings categories, copy the judge's score+severity into the gold entry
  (human status/note are preserved); if decision_mismatch, copy the judge
  decision. verdict=human_correct -> untouched. No other case is modified.
  Every copied value is verified against the sealed batch report; every
  input is hash-verified; any drift or unexpected adjudication fails closed.

Outputs (fresh --output dir, refuses overwrite): dev batch views, overlay
gold files, pb.gold.overlay.v1.json audit, manifest.json (input/output
sha256), INPUTS_SUMMARY.md. Zero model calls; deterministic (no wall-clock).
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_VERSION = '1.0.0'

DEFAULT_INPUTS = {
    'dev_orig_batch': 'outputs/p1_5.dev.v1.json',
    'dev_p2_batch': 'outputs/p2.judge.v2.json',
    'gold_orig': 'outputs/human_review/final.v1/human_gold.final.json',
    'gold_p2': 'outputs/human_review/p2.gold.v1/human_gold.p2.blind.json',
    'findings_p3': 'outputs/p3.findings.v1/calibration_findings_p3.json',
    'findings_pa': 'outputs/human_review/pa.adjudication.v1/pa_findings.json',
    'freeze_orig': 'outputs/rubrics_judge.node3.freeze.v4.json',
    'freeze_p2': 'outputs/p2.freeze.v5.json',
}
# sha256 pins for the two sealed findings files (verified at build time).
FINDINGS_SHA = {
    # byte sha of the SEALED output file (its internal provenance.findings_sha256
    # pins the upstream kit findings file, verified separately below)
    'findings_p3': '4542fdc60357907d646ea063830292a0a0ff99f1d58136892132ea1911c88954',
    'findings_pa': '63202e6bee148ef8f63a3f079b2a52e3918a5e06e8344d0b619f53f523292d3d',
}
# Correction spec: derived from sealed findings; values copied from the
# sealed judge batch and verified, never hand-transcribed.
CORRECTIONS = [
    {'code': 'C01', 'case_id': 'cal-interpreter-noise',
     'findings': 'findings_p3', 'dims': ['cleanliness'], 'decision': True},
    {'code': 'C02', 'case_id': 'cal-interpreter-instruction_interference',
     'findings': 'findings_p3',
     'dims': ['cleanliness', 'completeness', 'structure'], 'decision': True},
    {'code': 'A01', 'case_id': 'cal-appetite-reorder',
     'findings': 'findings_pa', 'dims': ['structure'], 'decision': True},
]
SEVERE = ('major', 'critical')


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def load_json(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def write_json(p, v):
    Path(p).write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n',
                       encoding='utf-8', newline='')


def _findings_entry(findings, case_id):
    for c in findings.get('cases', []):
        if c.get('case_id') == case_id:
            return c
    return None


def _check_categories(entry, dims, decision):
    cats = entry.get('categories') or []
    for d in dims:
        if not any(c.endswith(':' + d) for c in cats):
            raise ValueError('findings categories do not name dimension %s' % d)
    if decision and 'decision_mismatch' not in cats:
        raise ValueError('findings categories lack decision_mismatch')


def build(inputs, output):
    """Pure builder: inputs = {key: Path}, output = fresh dir Path."""
    out = Path(output)
    if out.exists():
        raise FileExistsError('output exists; choose a new directory')
    data = {}
    input_sha = {}
    for key, p in inputs.items():
        p = Path(p)
        b = p.read_bytes()
        input_sha[key] = sha256_bytes(b)
        data[key] = json.loads(b)
    for key, pin in FINDINGS_SHA.items():
        if input_sha[key] != pin:
            raise ValueError('%s sha256 drift (sealed findings altered?)' % key)
    # upstream chain: sealed P3 findings provenance pins the kit findings file
    kit = ROOT / 'outputs/human_review/p3.calibration.v1/p3_findings.json'
    if kit.exists():
        rec = data['findings_p3'].get('provenance', {}).get('findings_sha256')
        if sha256_bytes(kit.read_bytes()) != rec:
            raise ValueError('P3 kit findings upstream hash drift')

    b1, b2 = data['dev_orig_batch'], data['dev_p2_batch']
    g1, g2 = data['gold_orig'], data['gold_p2']
    f4, f5 = data['freeze_orig'], data['freeze_p2']
    fp3, fpa = data['findings_p3'], data['findings_pa']

    # --- batch views -----------------------------------------------------
    for row in b1['cases']:
        if row.get('split') != 'development':
            raise ValueError('orig batch contains non-dev case ' + row['case_id'])
    dev_p2 = [c for c in b2['cases'] if c.get('split') == 'development']
    excluded = [c['case_id'] for c in b2['cases'] if c.get('split') != 'development']
    if not dev_p2:
        raise ValueError('P2 batch has no development cases')
    for row in b2['cases']:
        if row.get('split') not in ('development', 'frozen_test'):
            raise ValueError('unexpected split in P2 batch: ' + row['case_id'])
    view2 = copy.deepcopy(b2)
    view2['cases'] = copy.deepcopy(dev_p2)
    view2['note'] = ((b2.get('note') or '') +
                     ' | P-B gate view: filtered to development split only '
                     '(%d cases); %d consumed frozen_test v2 cases excluded, '
                     'never re-scored.' % (len(dev_p2), len(excluded))).strip()
    # freeze integrity pre-check (same rules as score_p3_gate)
    for batch, freeze, label in ((b1, f4, 'orig'), (view2, f5, 'p2')):
        if batch.get('manifest_sha256') not in (freeze.get('files') or {}).values():
            raise ValueError('%s batch manifest hash not in freeze files' % label)
        frozen = {r['case_id']: r for r in freeze.get('cases', [])}
        for row in batch['cases']:
            frow = frozen.get(row['case_id'])
            if frow is None:
                raise ValueError('%s case not frozen: %s' % (label, row['case_id']))
            meta = row.get('case_meta') or {}
            for k in ('candidate_sha256', 'source_sha256', 'gold_sha256'):
                if k in frow and meta.get(k) != frow[k]:
                    raise ValueError('%s %s drift %s' % (label, k, row['case_id']))

    # --- gold subsets ----------------------------------------------------
    ids1 = {c['case_id'] for c in b1['cases']}
    ids2 = {c['case_id'] for c in dev_p2}
    gold1 = [c for c in g1['cases'] if c.get('case_id') in ids1]
    gold2 = [c for c in g2['cases'] if c.get('case_id') in ids2]
    if {c['case_id'] for c in gold1} != ids1:
        raise ValueError('orig gold missing dev cases')
    if {c['case_id'] for c in gold2} != ids2:
        raise ValueError('P2 gold missing dev cases')
    for c in gold1 + gold2:
        if c.get('split') != 'development':
            raise ValueError('gold entry not development: ' + c['case_id'])

    # --- adjudication coverage audit (fail closed on surprises) ----------
    dev_ids = ids1 | ids2
    unexpected = []
    for c in fp3.get('cases', []):
        if c.get('case_id') in dev_ids and c.get('verdict') == 'judge_correct':
            if c['case_id'] not in {x['case_id'] for x in CORRECTIONS}:
                unexpected.append(('p3', c['case_id']))
    for c in fpa.get('cases', []):
        if c.get('case_id') in dev_ids and c.get('verdict') == 'judge_correct':
            if c['case_id'] not in {x['case_id'] for x in CORRECTIONS}:
                unexpected.append(('pa', c['case_id']))
    if unexpected:
        raise ValueError('unhandled judge_correct dev adjudications: %r' % unexpected)

    # --- apply corrections ----------------------------------------------
    judge_by_id = {}
    for row in b1['cases'] + dev_p2:
        judge_by_id[row['case_id']] = row
    overlay_gold1 = copy.deepcopy(gold1)
    overlay_gold2 = copy.deepcopy(gold2)
    gold_by_id = {c['case_id']: c for c in overlay_gold1 + overlay_gold2}
    audit = []
    for spec in CORRECTIONS:
        cid = spec['case_id']
        findings = data[spec['findings']]
        entry = _findings_entry(findings, cid)
        if entry is None or entry.get('verdict') != 'judge_correct':
            raise ValueError('%s: sealed verdict is not judge_correct' % spec['code'])
        if spec['findings'] == 'findings_p3':
            _check_categories(entry, spec['dims'], spec['decision'])
        else:
            if entry.get('divergence_type') != 'v12_false_alarm':
                raise ValueError('%s: unexpected P-A divergence type' % spec['code'])
        jrow = judge_by_id.get(cid)
        if jrow is None or jrow.get('status') != 'accepted':
            raise ValueError('%s: no accepted sealed judge assessment' % spec['code'])
        ja = jrow['report']['assessment']
        gentry = gold_by_id[cid]
        before = {'decision': gentry.get('decision'),
                  'dimensions': {d: dict(gentry['dimensions'][d]) for d in spec['dims']}}
        for d in spec['dims']:
            jd = ja['dimensions'][d]
            gd = gentry['dimensions'][d]
            if jd.get('severity') not in SEVERE:
                raise ValueError('%s: judge %s not severe' % (spec['code'], d))
            if gd.get('severity') in SEVERE:
                raise ValueError('%s: gold %s already severe (no divergence)' % (spec['code'], d))
            gd['score'] = jd['score']
            gd['severity'] = jd['severity']
            # human status/note preserved; judge status recorded in audit only
        if spec['decision']:
            if ja['decision'] == gentry.get('decision'):
                raise ValueError('%s: decision already matches' % spec['code'])
            gentry['decision'] = ja['decision']
        gentry['overlay_note'] = (
            'P-B overlay %s (%s, verdict=judge_correct, sealed %s): '
            'dims %s <- judge v1.2 score+severity; decision <- judge. '
            'Original sealed gold unchanged.' % (
                spec['code'], cid, spec['findings'], ','.join(spec['dims'])))
        after = {'decision': gentry.get('decision'),
                 'dimensions': {d: dict(gentry['dimensions'][d]) for d in spec['dims']}}
        audit.append({
            'code': spec['code'], 'case_id': cid, 'verdict': 'judge_correct',
            'findings_source': spec['findings'],
            'findings_sha256': input_sha[spec['findings']],
            'judge_batch_sha256': input_sha['dev_orig_batch'] if cid in ids1
                                  else input_sha['dev_p2_batch'],
            'judge_version': jrow['report'].get('judge_version'),
            'rule': 'copy judge score+severity on divergent dims; copy judge '
                    'decision on mismatch; human status/note preserved',
            'before': before, 'after': after,
            'judge_status_recorded': {d: ja['dimensions'][d].get('status')
                                      for d in spec['dims']},
        })

    prov = {
        'overlay_version': 'pb-gold-overlay-1',
        'preregistration': 'docs/P_B_AMENDMENT_PROPOSAL.md',
        'branch': 'P3_GATE_PLAN step 4: no protocol revision; judge v1.2 frozen; '
                  'adjudicated-gold overlay (sealed gold never rewritten)',
        'base_gold_sha256': {'gold_orig': input_sha['gold_orig'],
                             'gold_p2': input_sha['gold_p2']},
        'corrections': [a['code'] for a in audit],
        'limitations': [
            'single annotator; IAA not measured (user waived second annotator)',
            'overlay adopts judge values on 3 adjudicated cases: partial anchoring '
            'circularity on the dev track; v3 is the independent generalization test',
            'agreement is not accuracy; sealed-gold mechanical track reported separately',
        ],
    }
    out1 = {'gold_version': 'pb-overlay-orig-1', 'stage': 'development',
            'annotator': g1.get('annotator'), 'provenance': prov,
            'cases': overlay_gold1}
    out2 = {'gold_version': 'pb-overlay-p2-1', 'stage': 'development',
            'annotator': g2.get('annotator'), 'provenance': prov,
            'cases': overlay_gold2}

    out.mkdir(parents=True)
    write_json(out / 'dev.orig.batch.json', b1)
    write_json(out / 'dev.p2.batch.json', view2)
    write_json(out / 'dev.orig.gold.json', out1)
    write_json(out / 'dev.p2.gold.json', out2)
    write_json(out / 'pb.gold.overlay.v1.json',
               {'tool_version': TOOL_VERSION, 'corrections': audit,
                'provenance': prov})
    output_sha = {p.name: sha256_bytes(p.read_bytes())
                  for p in sorted(out.iterdir()) if p.is_file()}
    manifest = {'tool_version': TOOL_VERSION, 'inputs': input_sha,
                'outputs': output_sha,
                'dev_cases': {'orig': sorted(ids1), 'p2': sorted(ids2)},
                'excluded_frozen_v2': sorted(excluded),
                'corrections': [a['code'] for a in audit],
                'discipline': 'zero model calls; sealed inputs read-only; '
                              'fail-closed hash verification; deterministic'}
    write_json(out / 'manifest.json', manifest)
    lines = ['# P-B gate inputs (zero-call, sealed-derived)', '',
             '- dev orig: %d cases (as-ran v1.2; iana x2 source_only, rest with_gold)' % len(ids1),
             '- dev P2: %d cases (filtered from %d; frozen_test v2 excluded)' % (len(dev_p2), len(b2['cases'])),
             '- overlay corrections: %s (all judge_correct, sealed findings)' % ', '.join(a['code'] for a in audit),
             '- sealed gold NOT rewritten; overlay is a derived artifact with full provenance.', '',
             '| code | case | before -> after |', '| --- | --- | --- |']
    for a in audit:
        b, af = a['before'], a['after']
        dims = '; '.join('%s %s/%s -> %s/%s' % (
            d, b['dimensions'][d].get('score'), b['dimensions'][d].get('severity'),
            af['dimensions'][d].get('score'), af['dimensions'][d].get('severity'))
            for d in a['after']['dimensions'])
        lines.append('| %s | %s | %s; decision %s -> %s |' % (
            a['code'], a['case_id'], dims, b['decision'], af['decision']))
    lines += ['', '局限：单标注者；overlay 3 例存在锚定循环性（dev 轨道）；v3 为独立泛化检验；一致率≠准确率。']
    (out / 'INPUTS_SUMMARY.md').write_text('\n'.join(lines) + '\n',
                                         encoding='utf-8', newline='')
    return manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description='P-B zero-call gate input builder.')
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--inputs-root', type=Path, default=ROOT)
    args = ap.parse_args(argv)
    inputs = {k: args.inputs_root / v for k, v in DEFAULT_INPUTS.items()}
    try:
        manifest = build(inputs, args.output)
    except FileExistsError as e:
        print(str(e), file=sys.stderr)
        return 3
    except (ValueError, KeyError) as e:
        print('FAIL-CLOSED: ' + str(e), file=sys.stderr)
        return 2
    print(json.dumps({'corrections': manifest['corrections'],
                      'dev_orig': len(manifest['dev_cases']['orig']),
                      'dev_p2': len(manifest['dev_cases']['p2']),
                      'output': str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
