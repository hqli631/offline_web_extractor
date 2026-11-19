"""P2 inter-annotator agreement (zero model calls).

Computes agreement between two independent annotators' blind labels: decision
Cohen kappa + match rate, dimension exact rate, severity sign rate, with
case-level bootstrap 95% CI (B=10000, fixed seed). Aligns cases by case_id (or
blind_code if case_id absent). IAA quantifies human gold noise; low IAA caps the
achievable judge-human agreement. Agreement is not accuracy.
"""
import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.ingest_human_labels import cohen_kappa

DIMS = ('completeness', 'cleanliness', 'structure', 'title', 'format')


def _load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def _cases(labels):
    cs = labels['cases'] if isinstance(labels, dict) else labels
    if isinstance(cs, dict):
        cs = list(cs.values())
    out = {}
    for c in cs:
        key = c.get('case_id') or c.get('blind_code')
        if key:
            out[key] = c
    return out


def _pairs(la, lb):
    a, b = _cases(la), _cases(lb)
    common = sorted(set(a) & set(b))
    return [(a[k], b[k], k) for k in common]


def m_match(pairs):
    return sum(x['decision'] == y['decision'] for x, y, _ in pairs) / len(pairs) if pairs else None


def m_kappa(pairs):
    return cohen_kappa([(x['decision'], y['decision']) for x, y, _ in pairs]) if pairs else None


def _dim_rate(pairs, key):
    num = den = 0
    for x, y, _ in pairs:
        for d in DIMS:
            dx, dy = x['dimensions'].get(d) or {}, y['dimensions'].get(d) or {}
            sx, sy = dx.get('score'), dy.get('score')
            if type(sx) is int and type(sy) is int:
                den += 1
                if key == 'exact':
                    num += int(sx == sy)
                else:
                    num += int((dx.get('severity') == 'none') == (dy.get('severity') == 'none'))
    return num / den if den else None


def m_dim_exact(pairs):
    return _dim_rate(pairs, 'exact')


def m_severity_sign(pairs):
    return _dim_rate(pairs, 'sign')


METRICS = {'decision_match_rate': m_match, 'decision_cohen_kappa': m_kappa,
           'dim_exact_rate': m_dim_exact, 'severity_sign_rate': m_severity_sign}


def bootstrap_ci(pairs, fn, B, seed):
    point = fn(pairs)
    n = len(pairs)
    if point is None or n == 0:
        return {'point': point, 'ci95': None, 'n': n}
    rng = random.Random(seed)
    vals = []
    for _ in range(B):
        s = [pairs[rng.randrange(n)] for _ in range(n)]
        v = fn(s)
        if v is not None:
            vals.append(v)
    vals.sort()
    return {'point': round(point, 4),
            'ci95': [round(vals[int(0.025 * len(vals))], 4), round(vals[min(len(vals) - 1, int(0.975 * len(vals)))], 4)],
            'n': n, 'B': len(vals)}


def main(argv=None):
    ap = argparse.ArgumentParser(description='P2 inter-annotator agreement + bootstrap CI.')
    ap.add_argument('--labels-a', type=Path, required=True)
    ap.add_argument('--labels-b', type=Path, required=True)
    ap.add_argument('--B', type=int, default=10000)
    ap.add_argument('--seed', type=int, default=20261119)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--md', type=Path, default=None)
    args = ap.parse_args(argv)
    if args.output.exists() or (args.md and args.md.exists()):
        print('Output exists; choose a new filename.', file=sys.stderr)
        return 3
    pairs = _pairs(_load(args.labels_a), _load(args.labels_b))
    metrics = {name: bootstrap_ci(pairs, fn, args.B, args.seed) for name, fn in METRICS.items()}
    disagreements = [{'key': k, 'a_decision': x['decision'], 'b_decision': y['decision']}
                     for x, y, k in pairs if x['decision'] != y['decision']]
    result = {'tool': 'compute_iaa.py', 'B': args.B, 'seed': args.seed,
              'n_common': len(pairs), 'metrics': metrics, 'decision_disagreements': disagreements,
              'inputs': {'a_sha256': hashlib.sha256(Path(args.labels_a).read_bytes()).hexdigest(),
                         'b_sha256': hashlib.sha256(Path(args.labels_b).read_bytes()).hexdigest()},
              'note': 'IAA quantifies human gold noise; low IAA caps judge-human agreement. Agreement is not accuracy.'}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='')
    if args.md:
        lines = ['# P2 inter-annotator agreement', '', 'n_common=%d; B=%d seed=%d' % (len(pairs), args.B, args.seed), '',
                 '| metric | point | 95% CI |', '| --- | --- | --- |']
        for name, m in metrics.items():
            ci = m['ci95']
            lines.append('| %s | %s | %s |' % (name, m['point'], ('[%s, %s]' % (ci[0], ci[1])) if ci else 'n/a'))
        lines += ['', 'decision disagreements: %d' % len(disagreements),
                  'IAA is not accuracy; low IAA limits achievable judge-human agreement.']
        args.md.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='')
    print(json.dumps({'output': str(args.output), 'n_common': len(pairs),
                      'kappa': metrics['decision_cohen_kappa']['point'],
                      'match': metrics['decision_match_rate']['point']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
