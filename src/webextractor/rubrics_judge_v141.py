"""Judge v1.4.1: missing-body anchor revision over the byte-frozen v1.2 judge.

P-F stage-1 finding (docs/P_F_STAGE1_REPORT.md): v1.4 fixed reorder/noise/
injection under-severing (3/3 + 3/3 + 1/1 followed) but the missing-body anchor
was systematically violated (2/2 accepted missing cases scored completeness
3/minor while explicitly acknowledging the missing paragraph). Root cause: the
v1.4 wording "scales with the magnitude" + "key body" left the model discretion
to classify a missing first/intro paragraph as a small local defect.

v1.4.1 changes EXACTLY ONE anchor (missing body): zero-discretion wording --
ANY meaningful body paragraph present in source/gold but absent from candidate
is SEVERE (completeness <= 2/major) regardless of position/length/importance;
first/intro paragraphs are key body; explicitly overrides the generic
3=small-local-defect scale for missing body. The other five anchors are
byte-identical to v1.4 (imported, verified by tests). v1.4 module stays
byte-frozen (pf.protocol.v1 pin); v1.2 base stays byte-frozen (edd841ef).

Post-hoc revision disclosed (docs/P_F_V141_PLAN.md): the 2 stage-1 missing
failures shaped this wording -> dev track circularity grows; v4 remains the
independent one-shot test, never exposed. v1.4.1 is NOT reward-eligible until
its own dev calibration + sealed v4 gate PASS.
"""
from copy import deepcopy
import hashlib
import json
import math
import time

from . import rubrics_judge as v12
from . import rubrics_judge_v14 as v14
from .rubrics_v2 import VERSION, score

JUDGE_VERSION = '1.4.1'
BASE_JUDGE_VERSION = v12.JUDGE_VERSION
BASE_SOURCE_SHA256 = v14.BASE_SOURCE_SHA256
PROTOCOL_ANCHORS_VERSION = 'v1.4.1'

MISSING_BODY_ANCHOR_V141 = (
    'PROTOCOL ANCHOR (missing body content, adjudicated, ZERO DISCRETION): ANY meaningful article body '
    'paragraph or block that exists in the source/gold but is absent from the candidate is a SEVERE '
    'completeness defect, regardless of its position, length or perceived importance: completeness <= 2 '
    'with severity major. The FIRST paragraph, the introduction, and every single body paragraph count as '
    'key body content. NEVER classify a missing body paragraph as minor or as a small local defect; this '
    'anchor OVERRIDES the generic 3=small-local-defect scale whenever body content is missing. Only '
    'large-scale loss (multiple paragraphs or most of the body) escalates to score 1 or 0 with critical. '
    'Whitespace-only or pure-formatting differences are not missing body. Cite the missing s:N or g:N content.'
)

# Five verified anchors byte-identical to v1.4; only the missing anchor revised.
PROTOCOL_ANCHORS_V141 = v14.PROTOCOL_ANCHORS_V14[:3] + (MISSING_BODY_ANCHOR_V141,) + v14.PROTOCOL_ANCHORS_V14[4:]


def _anchor_overhead():
    return len(json.dumps(list(PROTOCOL_ANCHORS_V141), ensure_ascii=False)) + len(PROTOCOL_ANCHORS_V141) + 64


def build_prompt(source, predicted, gold=None, *, max_source_chars=40000, max_prompt_chars=110000,
                 source_order_seed=None, dimension_phrasing=None):
    overhead = _anchor_overhead()
    if max_prompt_chars <= overhead:
        raise ValueError('Prompt budget too small for v1.4.1 protocol anchors')
    prompt, registry, metadata = v12.build_prompt(
        source, predicted, gold, max_source_chars=max_source_chars,
        max_prompt_chars=max_prompt_chars - overhead,
        source_order_seed=source_order_seed, dimension_phrasing=dimension_phrasing)
    prompt = deepcopy(prompt)
    prompt['protocol']['constraints'].extend(PROTOCOL_ANCHORS_V141)
    prompt['protocol']['protocol_anchors'] = PROTOCOL_ANCHORS_VERSION
    encoded = json.dumps(prompt, ensure_ascii=False)
    if len(encoded) > max_prompt_chars:
        raise ValueError('Prompt exceeds budget; use explicit source/window limits')
    metadata = dict(metadata, prompt_chars=len(encoded))
    return prompt, registry, metadata


def run_judge(source, predicted, provider, *, gold=None, max_source_chars=40000, max_output_tokens=2200,
              timeout_seconds=60, noise_terms=(), source_order_seed=None, dimension_phrasing=None,
              cached_response=None):
    # Execution semantics mirror v1.2/v1.4 exactly; only prompt/provenance differ.
    if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 32768:
        raise ValueError('Invalid token budget')
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (float, int)) \
            or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError('Invalid timeout')
    if cached_response is not None and not isinstance(cached_response, dict):
        raise ValueError('cached_response must be a provider response dict')
    prompt, registry, metadata = build_prompt(
        source, predicted, gold, max_source_chars=max_source_chars,
        source_order_seed=source_order_seed, dimension_phrasing=dimension_phrasing)
    started = time.monotonic()
    report = {'judge_version': JUDGE_VERSION, 'base_judge_version': BASE_JUDGE_VERSION,
              'protocol_anchors': PROTOCOL_ANCHORS_VERSION,
              'rubrics_version': VERSION, 'mode': prompt['protocol']['mode'],
              'requested_model': getattr(provider, 'model', None), 'provider': getattr(provider, 'name', None),
              'input': metadata,
              'prompt_sha256': hashlib.sha256(json.dumps(prompt, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
              'prompt': prompt, 'status': 'error', 'assessment': None, 'raw_content': None,
              'error': None, 'usage': None, 'cost': None,
              'cached': cached_response is not None,
              'program_assessment': score(predicted, gold, noise_terms=noise_terms,
                                          evidence_complete=not metadata['source_truncated'])}
    stage = 'provider'
    try:
        response = cached_response if cached_response is not None else provider.generate(
            prompt, timeout_seconds=timeout_seconds, max_output_tokens=max_output_tokens)
        stage = 'validation'
        for k in ('model', 'finish_reason', 'usage'):
            report[k] = response.get(k)
        report['raw_content'] = response.get('content')
        if response.get('finish_reason') != 'stop':
            raise ValueError('Judge response is not complete')
        if time.monotonic() - started > timeout_seconds:
            raise ValueError('Judge deadline exceeded')
        assessment = v12.validate_assessment(response['content'], registry)
        if metadata['source_truncated']:
            for d in assessment['dimensions'].values():
                if d['status'] == 'scored':
                    d['status'] = 'partial'
        dims = assessment['dimensions']
        severe = any(d['severity'] in ('major', 'critical') for d in dims.values())
        uncertain = any(d['status'] in ('partial', 'unscored') or d['severity'] != 'none' for d in dims.values())
        assessment['decision'] = 'fail' if severe else 'uncertain' if uncertain or gold is None else 'pass'
        assessment['needs_human_review'] = severe or uncertain or gold is None
        assessment['scope'] = 'Source-only provisional judgement' if gold is None else 'Reference-assisted uncalibrated judgement'
        report.update(status='accepted', assessment=assessment)
    except Exception as error:
        report['error'] = {'type': type(error).__name__, 'stage': stage,
                           'detail': str(error) if stage == 'validation' and isinstance(error, ValueError)
                           else 'Request failed; provider details suppressed'}
    report['elapsed_seconds'] = round(time.monotonic() - started, 3)
    report['settings'] = {'max_output_tokens': max_output_tokens, 'timeout_seconds': timeout_seconds,
                          'max_source_chars': max_source_chars, 'max_calls': 1,
                          'source_order_seed': source_order_seed, 'dimension_phrasing': dimension_phrasing}
    return report
