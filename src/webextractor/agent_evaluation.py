"""Gate 7 evaluation: keep Agent inputs separate from the gold/test layer."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from .agent_rules import execute_rule
from .rule_agent import run_agent


def _read_case(root: Path, case: dict[str, Any], *, expected: bool = False) -> tuple[bytes, dict | None]:
    payload = (root / case['html']).read_bytes()
    if hashlib.sha256(payload).hexdigest() != case['sha256']:
        raise ValueError(f"HTML hash mismatch: {case['id']}")
    answer = None
    if expected:
        answer = json.loads((root / case['expected']).read_text(encoding='utf-8-sig'))
        digest = hashlib.sha256((root / case['expected']).read_bytes()).hexdigest()
        if digest != case['expected_sha256']:
            raise ValueError(f"Expected hash mismatch: {case['id']}")
    return payload, answer


def load_manifest(path: str | Path) -> tuple[Path, dict, list[dict], list[dict]]:
    path = Path(path).resolve()
    manifest = json.loads(path.read_text(encoding='utf-8-sig'))
    if set(manifest) != {'protocol', 'references', 'tests'}:
        raise ValueError('Gate 7 manifest must contain protocol, references and tests')
    refs, tests = manifest['references'], manifest['tests']
    if not refs or not tests:
        raise ValueError('Gate 7 needs nonempty reference and test groups')
    seen = set()
    for group, split in ((refs, 'reference'), (tests, 'test')):
        for case in group:
            required = {'id', 'html', 'sha256', 'split'} | ({'expected', 'expected_sha256', 'expected_status'} if split == 'test' else set())
            if set(case) != required or case['split'] != split or case['id'] in seen:
                raise ValueError(f'Invalid {split} case fields or duplicate id')
            seen.add(case['id'])
            # Inspect only metadata here. Test HTML and gold must remain unread
            # until run_agent has returned; even hash validation reads content.
    reference_paths = {(path.parent / c['html']).resolve() for c in refs}
    reference_hashes = {c['sha256'].lower() for c in refs}
    if any((path.parent / c['html']).resolve() in reference_paths or
           c['sha256'].lower() in reference_hashes for c in tests):
        raise ValueError('Reference and test HTML paths/hashes must be disjoint')
    return path.parent, manifest, refs, tests


def _normalized_blocks(blocks: list[dict]) -> list[dict]:
    fields = ('kind', 'text', 'list_type', 'depth', 'ordinal',
              'heading_level', 'footnote_label', 'source_id')
    return [{name: block.get(name, 0 if name == 'depth' else None)
             for name in fields} for block in blocks]


def score_execution(execution: dict, expected: dict) -> dict:
    """Score only here, after the Agent has finished; expected is never prompt input."""
    actual = execution.get('result') or {}
    predicted = actual.get('blocks') or []
    gold = expected.get('blocks') or []
    pt, gt = Counter(b.get('text', '') for b in predicted), Counter(b.get('text', '') for b in gold)
    matched = sum((pt & gt).values())
    return {
        'status': execution.get('status'),
        'expected_status': expected.get('expected_status', 'ok'),
        'status_match': execution.get('status') == expected.get('expected_status', 'ok'),
        'title_exact': actual.get('title') == expected.get('title', '') if execution.get('result') else None,
        'block_text_precision': matched / sum(pt.values()) if pt else (1.0 if not gt else 0.0),
        'block_text_recall': matched / sum(gt.values()) if gt else (1.0 if not pt else 0.0),
        'blocks_exact': (_normalized_blocks(predicted) == _normalized_blocks(gold)
                         if gold and execution.get('result') else None),
    }


def evaluate_fixed_rule(manifest_path: str | Path, rule: dict, *, timeout_seconds: float = 5.0) -> dict:
    root, manifest, refs, tests = load_manifest(manifest_path)
    rows = []
    for case in tests:
        source, expected = _read_case(root, case, expected=True)
        execution = execute_rule(source, rule, timeout_seconds=timeout_seconds)
        rows.append({'id': case['id'], 'sha256': case['sha256'], 'execution': execution,
                     'metrics': score_execution(execution, expected)})
    return {'method': 'fixed-rule', 'manifest_sha256': hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest(),
            'rule': rule, 'reference_ids': [c['id'] for c in refs], 'cases': rows,
            'quality_evaluated': True}


def evaluate_agent(manifest_path: str | Path, provider, *, max_attempts: int = 3,
                   execution_timeout: float = 5.0, total_timeout: float = 60.0, max_output_tokens: int = 1024) -> dict:
    root, manifest, ref_cases, tests = load_manifest(manifest_path)
    # Only reference source bytes enter run_agent. Test HTML and expected answers
    # are loaded after generation and never occur in its prompt or trace.
    refs = [{'id': c['id'], 'source': _read_case(root, c)[0]} for c in ref_cases]
    trace = run_agent(refs, provider, max_attempts=max_attempts,
                      execution_timeout=execution_timeout, total_timeout=total_timeout, max_output_tokens=max_output_tokens)
    rows = []
    rule = trace.get('selected_rule')
    for case in tests:
        source, expected = _read_case(root, case, expected=True)
        execution = execute_rule(source, rule, timeout_seconds=execution_timeout) if rule else {
            'status': 'agent_no_rule', 'match_count': None, 'error': 'Agent did not select a rule', 'result': None}
        rows.append({'id': case['id'], 'sha256': case['sha256'], 'execution': execution,
                     'metrics': score_execution(execution, expected)})
    return {'method': 'agent', 'manifest_sha256': hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest(),
            'reference_ids': [c['id'] for c in ref_cases], 'trace': trace, 'cases': rows,
            'quality_evaluated': True}




