"""Bounded OpenAI-compatible provider for the constrained XPath Agent."""
from __future__ import annotations
import json, math, os, time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from .agent_rules import validate_rule

DEFAULT_BASE_URL = "https://tbnx.plus7.plus/v1"
ALLOWED_HOST = "tbnx.plus7.plus"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_RESPONSE_CHARS = 200_000

class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError("duplicate JSON key")
        result[key] = value
    return result

def _valid_usage(value):
    if not isinstance(value, dict): return None
    names = ("prompt_tokens", "completion_tokens", "total_tokens")
    if any(type(value.get(name)) is not int or value[name] < 0 for name in names): return None
    return {"input_tokens": value["prompt_tokens"], "output_tokens": value["completion_tokens"], "total_tokens": value["total_tokens"]}

def _parse_content(value):
    if isinstance(value, dict): return value
    if not isinstance(value, str) or len(value) > MAX_RESPONSE_CHARS: raise ValueError("model content is invalid or too large")
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines and lines[-1].strip() == "```" else lines[1:]).strip()
    try: result = json.loads(text, object_pairs_hook=_strict_object)
    except json.JSONDecodeError as error: raise ValueError("model content was not valid JSON") from error
    if not isinstance(result, dict): raise ValueError("model content must be a JSON object")
    return result

def _validate_metadata(payload, choice):
    model = payload.get("model")
    finish = choice.get("finish_reason")
    if model is not None and (not isinstance(model, str) or len(model) > 128):
        raise ValueError("response model metadata is invalid")
    if finish is not None and (not isinstance(finish, str) or len(finish) > 64):
        raise ValueError("finish reason metadata is invalid")
    return model, finish

class OpenAICompatibleProvider:
    name = "cc-switch-openai-compatible"
    def __init__(self, *, api_key=None, model=None, base_url=None, timeout_seconds=30.0, max_retries=0, opener=None, token_parameter="max_completion_tokens"):
        self.api_key = api_key or os.getenv("CCSWITCH_API_KEY")
        self.model = model or os.getenv("CCSWITCH_MODEL")
        self.base_url = (base_url or os.getenv("CCSWITCH_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.endpoint = self.base_url + "/chat/completions"
        self.timeout_seconds, self.max_retries = timeout_seconds, max_retries
        if token_parameter not in {"max_completion_tokens", "max_tokens"}: raise ValueError("unsupported token parameter")
        self.token_parameter = token_parameter
        self._validate_config()
        self._opener = opener or build_opener(_NoRedirect(), ProxyHandler({}))
    def _validate_config(self):
        parsed = urlparse(self.endpoint)
        try: port_ok = parsed.port in (None, 443)
        except ValueError: port_ok = False
        if (parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST or parsed.path != "/v1/chat/completions" or not port_ok or parsed.username or parsed.password or parsed.query or parsed.fragment): raise ValueError("base_url must be the approved CC Switch HTTPS endpoint")
        if not isinstance(self.api_key, str) or not self.api_key.strip(): raise ValueError("CCSWITCH_API_KEY is not configured")
        if not isinstance(self.model, str) or not self.model.strip() or len(self.model) > 128: raise ValueError("CCSWITCH_MODEL is invalid")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)) or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0: raise ValueError("timeout_seconds must be positive and finite")
        if type(self.max_retries) is not int or not 0 <= self.max_retries <= 1: raise ValueError("max_retries must be 0 or 1")
    def generate(self, prompt, *, timeout_seconds, max_output_tokens):
        if not isinstance(prompt, dict): raise ValueError("prompt must be a dictionary")
        if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 32768: raise ValueError("max_output_tokens is invalid")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0: raise ValueError("timeout_seconds must be positive and finite")
        deadline = time.monotonic() + min(self.timeout_seconds, timeout_seconds)
        body = {"model": self.model, "messages": [{"role": "system", "content": "Return only one JSON object for the constrained XPath rule."}, {"role": "user", "content": json.dumps(prompt, ensure_ascii=False, separators=(",", ":"))}], "temperature": 0, self.token_parameter: max_output_tokens}
        request = Request(self.endpoint, data=json.dumps(body, ensure_ascii=False).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.api_key}, method="POST")
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                remaining = deadline - time.monotonic()
                if remaining <= 0: raise TimeoutError("request budget exhausted")
                with self._opener.open(request, timeout=remaining) as response: raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES: raise ValueError("response exceeded local byte limit")
                payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
                choice = payload["choices"][0]
                if choice.get("finish_reason") == "length": raise ValueError("model response was truncated")
                model, finish_reason = _validate_metadata(payload, choice)
                if choice["message"].get("refusal"): raise ValueError("model refused rule generation")
                content = validate_rule(_parse_content(choice["message"]["content"]))
                return {"content": content, "usage": _valid_usage(payload.get("usage")), "model": model, "finish_reason": finish_reason}
            except HTTPError as error:
                last_error = error
                if error.code not in {408, 429, 500, 502, 503, 504} or attempt >= self.max_retries: break
            except (URLError, TimeoutError, OSError) as error:
                last_error = error
                if attempt >= self.max_retries: break
            except (ValueError, KeyError, IndexError, TypeError) as error:
                last_error = error; break
        status = f" HTTP {last_error.code}" if isinstance(last_error, HTTPError) else ""
        raise RuntimeError(f"CC Switch request failed:{status} {type(last_error).__name__}") from None

