"""P2 bootstrap statistics (zero model calls).

Case-level bootstrap 95% CI (B=10000, fixed seed) for judge-human agreement
metrics on development batches: decision match rate, Cohen kappa, dim exact,
severity sign, severe_miss/false_alarm rate, reject rate. Paired comparison of
two batches: McNemar exact test on decision correctness + bootstrap CI of the
match-rate difference over commonly-accepted cases. Reuses ingest_human_labels
metric semantics. Agreement is not accuracy; dev is not generalization.
"""
import argparse
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.ingest_human_labels import compare_human_case, cohen_kappa

ROOT = Path(__file__).resolve().parents[1]
DIMS = ('completeness', 'cleanliness', 'structure', 'title', 'format')


def _load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def _gold_map(gold):
    cases = gold['cases'] if isinstance(gold, dict) else gold
    if isinstance(cases, dict):
        cases = list(cases.values())
    return {c['case_id']: c for c in cases}


def _records(batch, gold_map, silver_dir):
    recs = []
    for row in batch['cases']:
        if row['split'] != 'development':
            continue
        cid = row['case_id']
        entry = gold_map.get(cid)
        if entry is None:
            raise ValueError('No human gold for ' + cid)
        sp = Path(silver_dir) / (cid + '.label.json')
        silver = _load(sp) if sp.exists() else None
        r, _ = compare_human_case(row, entry, silver)
        recs.append(r)
    return recs


def _accepted(recs):
    return [r for r in recs if r['judge_status'] == 'accepted']


def m_decision_match(recs):
    a = _accepted(recs)
    return sum(r['decision_match'] for r in a) / len(a) if a else None


def m_kappa(recs):
    a = _accepted(recs)
    if not a:
        return None
    return cohen_kappa([(r['judge_decision'], r['human_decision']) for r in a])


def _dim_rate(recs, key):
    a = _accepted(recs)
    comp = [d for r in a for d in r['dimensions'].values() if d['comparable']]
    return sum(d[key] for d in comp) / len(comp) if comp else None


def m_dim_exact(recs):
    return _dim_rate(recs, 'exact')


def m_severity_sign(recs):
    return _dim_rate(recs, 'severity_sign_match')


def m_severe_miss(recs):
    a = _accepted(recs)
    return sum(bool(r.get('severe_miss')) for r in a) / len(a) if a else None


def m_false_alarm(recs):
    a = _accepted(recs)
    return sum(bool(r.get('false_alarm')) for r in a) / len(a) if a else None


def m_reject(recs):
    return sum(r['judge_status'] != 'accepted' for r in recs) / len(recs) if recs else None


METRICS = {'decision_match_rate': m_decision_match, 'decision_cohen_kappa': m_kappa,
           'dim_exact_rate': m_dim_exact, 'severity_sign_rate': m_severity_sign,
           'severe_miss_rate': m_severe_miss, 'false_alarm_rate': m_false_alarm,
           'reject_rate': m_reject}


def bootstrap_ci(recs, fn, B, seed):
    point = fn(recs)
    n = len(recs)
    if point is None or n == 0:
        return {'point': point, 'ci95': None, 'n': n}
    rng = random.Random(seed)
    vals = []
    for _ in range(B):
        sample = [recs[rng.randrange(n)] for _ in range(n)]
        v = fn(sample)
        if v is not None:
            vals.append(v)
    vals.sort()
    lo = vals[int(0.025 * len(vals))]
    hi = vals[min(len(vals) - 1, int(0.975 * len(vals)))]
    return {'point': round(point, 4), 'ci95': [round(lo, 4), round(hi, 4)], 'n': n, 'B': len(vals)}


def _mcnemar_exact(b, c):
    # two-sided exact binomial p on discordant pairs b, c
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) * (0.5 ** n)
    return min(1.0, 2 * tail)


def paired(recsA, recsB, B, seed):
    a = {r['case_id']: r for r in _accepted(recsA)}
    b = {r['case_id']: r for r in _accepted(recsB)}
    common = sorted(set(a) & set(b))
    if not common:
        return None
    bb = cc = 0
    pairs = []
    for cid in common:
        ma, mb = bool(a[cid]['decision_match']), bool(b[cid]['decision_match'])
        pairs.append((ma, mb))
        if ma and not mb:
            bb += 1
        elif mb and not ma:
            cc += 1
    rng = random.Random(seed)
    diffs = []
    n = len(pairs)
    for _ in range(B):
        s = [pairs[rng.randrange(n)] for _ in range(n)]
        da = sum(x for x, _ in s) / n
        db = sum(y for _, y in s) / n
        diffs.append(da - db)
    diffs.sort()
    lo = diffs[int(0.025 * len(diffs))]
    hi = diffs[min(len(diffs) - 1, int(0.975 * len(diffs)))]
    point = sum(x for x, _ in pairs) / n - sum(y for _, y in pairs) / n
    return {'common_accepted': n, 'A_correct_B_wrong': bb, 'A_wrong_B_correct': cc,
            'mcnemar_exact_p': round(_mcnemar_exact(bb, cc), 4),
            'match_diff_A_minus_B': round(point, 4),
            'diff_ci95': [round(lo, 4), round(hi, 4)]}


def main(argv=None):
    ap = argparse.ArgumentParser(description='P2 bootstrap CI + paired comparison (dev only).')
    ap.add_argument('--gold', type=Path, default=ROOT / 'outputs/human_review/final.v1/human_gold.final.json')
    ap.add_argument('--silver-dir', type=Path, default=ROOT / 'samples/calibration/labels')
    ap.add_argument('--batch', action='append', required=True, help='label=path (dev batch); repeatable')
    ap.add_argument('--B', type=int, default=10000)
    ap.add_argument('--seed', type=int, default=20261119)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--md', type=Path, default=None)
    args = ap.parse_args(argv)
    if args.output.exists() or (args.md and args.md.exists()):
        print('Output exists; choose a new filename.', file=sys.stderr)
        return 3
    gold_map = _gold_map(_load(args.gold))
    batches = {}
    for spec in args.batch:
        label, path = spec.split('=', 1)
        batches[label] = _records(_load(path), gold_map, args.silver_dir)
    result = {'tool': 'bootstrap_stats.py', 'B': args.B, 'seed': args.seed,
              'scope': 'development_only', 'gold_sha256': None,
              'batches': {}, 'paired': {}}
    import hashlib
    result['gold_sha256'] = hashlib.sha256(Path(args.gold).read_bytes()).hexdigest()
    for label, recs in batches.items():
        result['batches'][label] = {'n_dev': len(recs),
                                    'metrics': {name: bootstrap_ci(recs, fn, args.B, args.seed)
                                                for name, fn in METRICS.items()}}
    labels = list(batches)
    for i in range(len(labels) - 1):
        la, lb = labels[i], labels[i + 1]
        result['paired'][la + '_vs_' + lb] = paired(batches[la], batches[lb], args.B, args.seed)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='')
    if args.md:
        lines = ['# P2 bootstrap statistics (development only)', '',
                 'B=%d seed=%d; case-level resampling; agreement is not accuracy; dev is not generalization.' % (args.B, args.seed), '']
        for label, b in result['batches'].items():
            lines += ['## %s (n_dev=%d)' % (label, b['n_dev']), '', '| metric | point | 95% CI |', '| --- | --- | --- |']
            for name, m in b['metrics'].items():
                ci = m['ci95']
                lines.append('| %s | %s | %s |' % (name, m['point'], ('[%s, %s]' % (ci[0], ci[1])) if ci else 'n/a'))
            lines.append('')
        for name, p in result['paired'].items():
            if p:
                lines += ['## paired %s' % name,
                          '- common accepted: %d; McNemar exact p=%s; match diff (A-B)=%s CI %s' % (p['common_accepted'], p['mcnemar_exact_p'], p['match_diff_A_minus_B'], p['diff_ci95']), '']
        args.md.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='')
    print(json.dumps({'output': str(args.output), 'batches': list(batches),
                      'paired': list(result['paired'])}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
