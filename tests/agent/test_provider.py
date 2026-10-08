import json

import pytest

from retailpulse.agent.contracts import KpiCall, KpiRequest, Plan
from retailpulse.agent.provider import Ollama, ProviderError, _NoRedirect


def plan():
    return Plan(call=KpiCall(tool="get_kpi", arguments=KpiRequest(metric="data_freshness")))


@pytest.mark.parametrize("endpoint", ["https://example.com", "http://localhost.evil", "file:///etc/passwd", "http://127.0.0.1@evil.test", "http://localhost:11434", "http://127.0.0.1:11434/path", "http://127.0.0.1:11434?key=secret"])
def test_loopback_only(endpoint):
    with pytest.raises(ValueError):
        Ollama("test",endpoint=endpoint)


@pytest.mark.parametrize("content", [
    '{"call":{"tool":"execute_sql","arguments":{"sql":"DROP TABLE x"}}}',
    '{"call":{"tool":"get_kpi","arguments":{"metric":"data_freshness"}},"answer":"Sales are 999999"}',
    "not json", "[]", "null",
])
def test_hallucinated_or_unsupported_provider_output(content, monkeypatch):
    provider = Ollama("mock")
    monkeypatch.setattr(provider, "_request", lambda *a,**kw: {"message":{"content":content}})
    with pytest.raises(ProviderError):
        provider.select("How fresh is the data?",plan())


def test_schema_and_valid_proposal(monkeypatch):
    provider = Ollama("mock")
    def transport(path,payload):
        assert path == "/api/chat" and payload["stream"] is False
        assert payload["format"]["additionalProperties"] is False
        assert payload["options"]["num_predict"] <= 600
        return {"message":{"content":plan().model_dump_json()}}
    monkeypatch.setattr(provider,"_request",transport)
    assert provider.select("How fresh is the data?",plan()) == plan()


def test_redirect_is_never_followed():
    with pytest.raises(ProviderError):
        _NoRedirect().redirect_request(None,None,302,"",{},"https://example.com")


def test_transport_timeout_and_size(monkeypatch):
    class Response:
        def __init__(self, body): self.body=body
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read1(self,n):
            chunk,self.body=self.body[:n],self.body[n:]
            return chunk
    class Opener:
        def open(self,request,timeout):
            assert request.full_url == "http://127.0.0.1:11434/api/tags" and timeout <= 2
            return Response(json.dumps({"models":[{"name":"mock:latest"}]}).encode())
    monkeypatch.setattr("retailpulse.agent.provider.build_opener",lambda *args: Opener())
    assert Ollama("mock").models() == ["mock:latest"]
    monkeypatch.setattr(Opener,"open",lambda *a,**kw: Response(b"x"*65537))
    with pytest.raises(ProviderError,match="response_too_large"):
        Ollama("mock").models()
    def timeout(*args,**kwargs): raise TimeoutError()
    monkeypatch.setattr(Opener,"open",timeout)
    with pytest.raises(ProviderError,match="unavailable_or_timeout"):
        Ollama("mock").models()
