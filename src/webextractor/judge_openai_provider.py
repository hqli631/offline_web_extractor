"""Judge-compatible OpenAI-compatible provider for P2 cross-family cross-judge.

Independent from the production rule-agent OpenAICompatibleProvider (which
validates XPath rules) and from the production Qwen judge. Reuses parsing/helpers
from openai_provider but applies the JUDGE system message and does NOT validate
rule content, so run_judge can consume it via the standard provider interface
(.generate -> {content, model, finish_reason, usage}). For cross-family judge
experiments (e.g. gpt-5.6-sol via CC Switch); zero production judge changes.
"""
from __future__ import annotations
import json
import math
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request

from .openai_provider import (DEFAULT_BASE_URL, MAX_RESPONSE_BYTES, _NoRedirect,
                              _strict_object, _valid_usage, _validate_metadata,
                              _parse_content)
from .rubrics_judge import QwenJudgeProvider
from urllib.request import ProxyHandler, build_opener


class JudgeOpenAIProvider:
    name = 'cc-switch-judge'
    system_message = QwenJudgeProvider.system_message

    def __init__(self, *, api_key=None, model=None, base_url=None, timeout_seconds=30.0,
                 max_retries=0, opener=None, token_parameter='max_completion_tokens'):
        self.api_key = api_key or os.getenv('CCSWITCH_API_KEY')
        self.model = model or os.getenv('CCSWITCH_MODEL') or 'gpt-5.6-sol'
        self.base_url = (base_url or os.getenv('CCSWITCH_BASE_URL') or DEFAULT_BASE_URL).rstrip('/')
        self.endpoint = self.base_url + '/chat/completions'
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        if token_parameter not in {'max_completion_tokens', 'max_tokens'}:
            raise ValueError('unsupported token parameter')
        self.token_parameter = token_parameter
        if not self.api_key:
            raise ValueError('CCSWITCH_API_KEY required')
        if opener is not None:
            self._opener = opener
        else:
            self._opener = build_opener(ProxyHandler({}), _NoRedirect())

    def generate(self, prompt, *, timeout_seconds, max_output_tokens):
        if not isinstance(prompt, dict):
            raise ValueError('prompt must be a dictionary')
        if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 32768:
            raise ValueError('max_output_tokens is invalid')
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError('timeout_seconds must be positive and finite')
        deadline = time.monotonic() + min(self.timeout_seconds, timeout_seconds)
        body = {'model': self.model,
                'messages': [{'role': 'system', 'content': self.system_message},
                             {'role': 'user', 'content': json.dumps(prompt, ensure_ascii=False, separators=(',', ':'))}],
                'temperature': 0, self.token_parameter: max_output_tokens}
        request = Request(self.endpoint, data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
                          headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.api_key},
                          method='POST')
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('request budget exhausted')
                with self._opener.open(request, timeout=remaining) as response:
                    raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise ValueError('response exceeded local byte limit')
                payload = json.loads(raw.decode('utf-8'), object_pairs_hook=_strict_object)
                choice = payload['choices'][0]
                if choice.get('finish_reason') == 'length':
                    raise ValueError('model response was truncated')
                model, finish_reason = _validate_metadata(payload, choice)
                if choice['message'].get('refusal'):
                    raise ValueError('model refused judgement')
                content = _parse_content(choice['message']['content'])
                return {'content': content, 'usage': _valid_usage(payload.get('usage')),
                        'model': model, 'finish_reason': finish_reason}
            except HTTPError as error:
                last_error = error
                if error.code not in {408, 429, 500, 502, 503, 504} or attempt >= self.max_retries:
                    break
            except (URLError, TimeoutError, OSError) as error:
                last_error = error
                if attempt >= self.max_retries:
                    break
            except (ValueError, KeyError, IndexError, TypeError) as error:
                last_error = error
                break
        status = f' HTTP {last_error.code}' if isinstance(last_error, HTTPError) else ''
        raise RuntimeError(f'CC Switch judge request failed:{status} {type(last_error).__name__}') from None
