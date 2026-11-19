import json, unittest
from src.webextractor.openai_provider import OpenAICompatibleProvider, _NoRedirect

class Response:
    def __init__(self,payload): self.payload=payload
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,limit=-1): return json.dumps(self.payload).encode()
class Opener:
    def __init__(self,payload): self.payload,self.calls=payload,0
    def open(self,request,timeout): self.calls+=1; return Response(self.payload)
class Tests(unittest.TestCase):
    def payload(self): return {"model":"gpt-5.6-sol","choices":[{"finish_reason":"stop","message":{"content":"{\"version\":1,\"container_xpath\":\"//main\",\"exclude_xpaths\":[]}"}}],"usage":{"prompt_tokens":2,"completion_tokens":3,"total_tokens":5}}
    def test_mapping(self):
        o=Opener(self.payload()); p=OpenAICompatibleProvider(api_key="secret",model="gpt-5.6-sol",opener=o); r=p.generate({},timeout_seconds=2,max_output_tokens=32); self.assertEqual(r["content"]["version"],1); self.assertEqual(r["usage"]["total_tokens"],5); self.assertEqual(o.calls,1)
    def test_endpoint_and_redirect(self):
        with self.assertRaises(ValueError): OpenAICompatibleProvider(api_key="x",model="m",base_url="https://evil.example/v1")
        self.assertIsNone(_NoRedirect().redirect_request(None,None,302,"",{},"https://evil.example"))
    def test_invalid_json_not_retried(self):
        o=Opener({"choices":[]}); p=OpenAICompatibleProvider(api_key="secret",model="m",opener=o,max_retries=1)
        with self.assertRaisesRegex(RuntimeError,"IndexError"): p.generate({},timeout_seconds=2,max_output_tokens=32)
        self.assertEqual(o.calls,1)
if __name__ == "__main__": unittest.main()
