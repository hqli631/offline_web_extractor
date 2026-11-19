"""Optional DashScope-compatible provider for the bounded rule Agent."""
from __future__ import annotations
import json, math, os, time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
DEFAULT_ENDPOINT = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
ALLOWED_HOSTS = frozenset({"dashscope.aliyuncs.com", "dashscope-intl.aliyuncs.com"})
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class _NoRedirect(HTTPRedirectHandler):
    """Do not forward an Authorization header to a redirected host."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key in provider response")
        result[key] = value
    return result


def _valid_usage(value):
    if not isinstance(value, dict):
        return None
    names = ("prompt_tokens", "completion_tokens", "total_tokens")
    if any(type(value.get(name)) is not int or value[name] < 0 for name in names):
        return None
    return {"input_tokens": value["prompt_tokens"],
            "output_tokens": value["completion_tokens"],
            "total_tokens": value["total_tokens"]}


class QwenProvider:
    name = "qwen-dashscope"
    system_message = 'Return only a JSON object for the constrained XPath rule.'
    def __init__(self, *, api_key=None, model="qwen-plus", endpoint=DEFAULT_ENDPOINT, proxy=None, timeout_seconds=30.0, max_retries=1, opener=None):
        self.api_key = api_key or os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        self.model, self.endpoint = model, endpoint
        self.timeout_seconds, self.max_retries = timeout_seconds, max_retries
        self._validate_config()
        if opener is not None: self._opener = opener
        elif proxy:
            parsed = urlparse(proxy)
            if (parsed.scheme not in {"http", "https"} or
                    parsed.hostname not in {"127.0.0.1", "localhost"} or
                    parsed.username is not None or parsed.password is not None or
                    parsed.query or parsed.fragment):
                raise ValueError("proxy must be an explicit local HTTP(S) proxy")
            try:
                if parsed.port not in (None, 80, 443, 7897):
                    raise ValueError("proxy port is not allowed")
            except ValueError:
                raise ValueError("proxy port is not allowed") from None
            self._opener = build_opener(_NoRedirect(), ProxyHandler({"http": proxy, "https": proxy}))
        else:
            # Never inherit HTTP_PROXY/HTTPS_PROXY implicitly. A caller must
            # opt in to the local Clash proxy or provide an opener in tests.
            self._opener = build_opener(_NoRedirect(), ProxyHandler({}))
    def _validate_config(self):
        parsed = urlparse(self.endpoint)
        try:
            port_ok = parsed.port in (None, 443)
        except ValueError:
            port_ok = False
        if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or
                parsed.path != "/compatible-mode/v1/chat/completions" or
                not port_ok or parsed.username is not None or
                parsed.password is not None or parsed.query or parsed.fragment):
            raise ValueError("endpoint must be an allowed DashScope compatible chat endpoint")
        if not isinstance(self.model, str) or not self.model or len(self.model) > 128: raise ValueError("model must be a nonempty short string")
        if not isinstance(self.api_key, str) or not self.api_key.strip(): raise ValueError("Qwen API key is not configured")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int,float)) or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0: raise ValueError("timeout_seconds must be a positive finite number")
        if type(self.max_retries) is not int or not 0 <= self.max_retries <= 1: raise ValueError("max_retries must be 0 or 1")
    @staticmethod
    def _content(payload):
        try: content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error: raise ValueError("Qwen response did not contain a chat message") from error
        if isinstance(content, str):
            text = content.strip()
            if text.startswith("```"):
                text = text.split("\n",1)[1] if "\n" in text else text[3:]
                if text.rstrip().endswith("```"): text = text.rstrip()[:-3].rstrip()
            try: content = json.loads(text, object_pairs_hook=_strict_object)
            except json.JSONDecodeError as error: raise ValueError("Qwen response was not valid JSON rule content") from error
        if not isinstance(content, dict): raise ValueError("Qwen message content must be a JSON object")
        return content
    def generate(self, prompt, *, timeout_seconds, max_output_tokens):
        if not isinstance(prompt, dict): raise ValueError("prompt must be a dictionary")
        if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 32768: raise ValueError("max_output_tokens is outside the supported range")
        if (isinstance(timeout_seconds, bool) or
                not isinstance(timeout_seconds, (int, float)) or
                not math.isfinite(timeout_seconds) or timeout_seconds <= 0):
            raise ValueError("timeout_seconds must be a positive finite number")
        deadline = time.monotonic() + min(self.timeout_seconds, timeout_seconds)
        timeout = max(0.001, deadline - time.monotonic())
        if timeout <= 0: raise TimeoutError("Qwen request budget is exhausted")
        body = {"model": self.model, "messages": [{"role": "system", "content": self.system_message}, {"role": "user", "content": json.dumps(prompt, ensure_ascii=False, separators=(",",":"))}], "temperature": 0, "max_tokens": max_output_tokens}
        if self.model.startswith('qwen3'):
            body['enable_thinking'] = False
        request = Request(self.endpoint, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.api_key}, method="POST")
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Qwen request budget is exhausted")
                with self._opener.open(request, timeout=remaining) as response:
                    raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    raise ValueError("Qwen response exceeded the local byte limit")
                payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
                content = self._content(payload)
                choice = payload['choices'][0]
                if choice.get('finish_reason') == 'length':
                    raise ValueError('Qwen response was truncated')
                usage = payload.get("usage")
                return {"content": content, "usage": _valid_usage(usage),
                        'model': payload.get('model'), 'finish_reason': choice.get('finish_reason')}
            except HTTPError as error:
                last_error = error
                if error.code not in {408,429,500,502,503,504} or attempt >= self.max_retries: break
            except (URLError, TimeoutError, OSError) as error:
                last_error = error
                if attempt >= self.max_retries: break
            except ValueError as error:
                # Schema/JSON/size failures are deterministic and retrying can
                # spend another request without changing the response.
                last_error = error
                break
        status = f' HTTP {last_error.code}' if isinstance(last_error, HTTPError) else ''
        raise RuntimeError(f"Qwen request failed after {attempt + 1} attempt(s): {type(last_error).__name__}{status}") from None
