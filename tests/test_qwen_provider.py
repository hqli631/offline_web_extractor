import json, os, unittest
from unittest.mock import patch
from urllib.error import URLError
from src.webextractor.qwen_provider import QwenProvider, _NoRedirect
class Response:
    def __init__(self,payload): self.payload=payload
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self, limit=-1):
        raw = json.dumps(self.payload).encode()
        return raw if limit < 0 else raw[:limit]
class Opener:
    def __init__(self,payload): self.payload,self.calls=payload,0
    def open(self,request,timeout): self.calls+=1; return Response(self.payload)
class Tests(unittest.TestCase):
    def test_qwen_key_priority_and_qwen3_metadata(self):
        class CapturingOpener(Opener):
            def open(self, request, timeout):
                self.request_body = json.loads(request.data)
                return super().open(request, timeout)
        opener = CapturingOpener({'model':'qwen3.8-27b','choices':[{'finish_reason':'stop','message':{'content':{'version':1,'container_xpath':'//main','exclude_xpaths':[]}}}]})
        with patch.dict(os.environ, {'QWEN_API_KEY':'new-key','DASHSCOPE_API_KEY':'old-key'}):
            provider = QwenProvider(model='qwen3.8-27b', opener=opener)
        self.assertEqual(provider.api_key, 'new-key')
        result = provider.generate({}, timeout_seconds=2, max_output_tokens=64)
        self.assertFalse(opener.request_body['enable_thinking'])
        self.assertEqual(result['model'], 'qwen3.8-27b')
        self.assertEqual(result['finish_reason'], 'stop')

    def test_truncated_response_is_not_accepted(self):
        provider, opener = self.make({'choices':[{'finish_reason':'length','message':{'content':{'version':1}}}]})
        with self.assertRaisesRegex(RuntimeError, 'ValueError'):
            provider.generate({}, timeout_seconds=2, max_output_tokens=20)
        self.assertEqual(opener.calls, 1)

    def make(self,payload):
        opener=Opener(payload); return QwenProvider(api_key="test-key",opener=opener),opener
    def test_mapping(self):
        p,o=self.make({"choices":[{"message":{"content":"{\"version\":1,\"container_xpath\":\"//article\",\"exclude_xpaths\":[]}"}}],"usage":{"prompt_tokens":3,"completion_tokens":4,"total_tokens":7}})
        r=p.generate({"evidence":"x"},timeout_seconds=2,max_output_tokens=20)
        self.assertEqual(r["content"]["version"],1); self.assertEqual(r["usage"]["output_tokens"],4); self.assertEqual(o.calls,1)
    def test_validation(self):
        with self.assertRaises(ValueError): QwenProvider(api_key="x",endpoint="https://evil.example/chat")
        with self.assertRaises(ValueError): QwenProvider(api_key="x",proxy="http://10.0.0.1:7897")
        for endpoint in [
            "https://dashscope.aliyuncs.com:444/compatible-mode/v1/chat/completions",
            "https://user:pass@dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions?x=1",
        ]:
            with self.assertRaises(ValueError): QwenProvider(api_key="x", endpoint=endpoint)
        with self.assertRaises(ValueError): QwenProvider(api_key="x", proxy="http://127.0.0.1:7897?x=1")

    def test_invalid_json_is_not_retried(self):
        opener = Opener({"choices": []})
        provider = QwenProvider(api_key="test-key", opener=opener, max_retries=1)
        with self.assertRaisesRegex(RuntimeError, "ValueError"):
            provider.generate({}, timeout_seconds=2, max_output_tokens=20)
        self.assertEqual(opener.calls, 1)

    def test_response_size_limit_is_not_retried(self):
        class HugeResponse(Response):
            def read(self, limit=-1):
                return b"x" * (2 * 1024 * 1024 + 1)
        class HugeOpener(Opener):
            def open(self, request, timeout):
                self.calls += 1
                return HugeResponse({})
        opener = HugeOpener({})
        provider = QwenProvider(api_key="test-key", opener=opener, max_retries=1)
        with self.assertRaisesRegex(RuntimeError, "ValueError"):
            provider.generate({}, timeout_seconds=2, max_output_tokens=20)
        self.assertEqual(opener.calls, 1)

    def test_retry_uses_remaining_budget(self):
        class RetryOpener(Opener):
            def __init__(self):
                super().__init__({"choices": [{"message": {"content": {"version": 1}}}]})
                self.timeouts = []
            def open(self, request, timeout):
                self.calls += 1
                self.timeouts.append(timeout)
                if self.calls == 1:
                    raise URLError("temporary failure")
                return Response(self.payload)
        opener = RetryOpener()
        provider = QwenProvider(api_key="test-key", opener=opener, timeout_seconds=10)
        with patch('src.webextractor.qwen_provider.time.monotonic', side_effect=[0, 0, 1, 7]):
            provider.generate({}, timeout_seconds=10, max_output_tokens=20)
        self.assertEqual(opener.timeouts, [9, 3])

    def test_default_opener_disables_redirects_and_implicit_proxy(self):
        with patch('src.webextractor.qwen_provider.build_opener') as builder:
            QwenProvider(api_key="test-key")
        handlers = builder.call_args.args
        self.assertTrue(any(isinstance(h, _NoRedirect) for h in handlers))
        self.assertEqual(next(h for h in handlers if hasattr(h, 'proxies')).proxies, {})
        self.assertIsNone(_NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.example'))
    def test_error_redacts_key(self):
        p,_=self.make({"choices":[]})
        with self.assertRaisesRegex(RuntimeError,"ValueError") as ctx: p.generate({},timeout_seconds=2,max_output_tokens=20)
        self.assertNotIn("test-key",str(ctx.exception))
if __name__=="__main__": unittest.main()
