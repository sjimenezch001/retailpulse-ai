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
    monkeypatch.setattr(provider, "_request", lambda *a,**kw: {"done":True,"done_reason":"stop","message":{"content":content}})
    with pytest.raises(ProviderError):
        provider.select("How fresh is the data?",plan())


def test_schema_and_valid_proposal(monkeypatch):
    provider = Ollama("mock")
    def transport(path,payload):
        assert path == "/api/chat" and payload["stream"] is False
        assert payload["format"]["additionalProperties"] is False
        assert payload["options"]["num_predict"] <= 600
        message = json.loads(payload["messages"][1]["content"])
        assert message["candidate"] == plan().model_dump(mode="json")
        assert "verbatim" in payload["messages"][0]["content"]
        return {"done":True,"done_reason":"stop","message":{"content":plan().model_dump_json()}}
    monkeypatch.setattr(provider,"_request",transport)
    assert provider.select("How fresh is the data?",plan()) == plan()
    assert provider.last_diagnostic.status == "succeeded"


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
    with pytest.raises(ProviderError,match="timeout"):
        Ollama("mock").models()


@pytest.mark.parametrize("response, category", [
    ({"error":"PRIVATE_TOKEN"}, "api_error"),
    ({"done":False}, "generation_incomplete"),
    ({"done":True,"done_reason":"length"}, "generation_truncated"),
    ({"done":True,"message":{"content":"PRIVATE_TOKEN invalid JSON"}}, "invalid_selection_json"),
    ({"done":True,"message":{"content":'{"call":{"tool":"PRIVATE_TOKEN"}}'}}, "schema_validation"),
    ({"done":True,"message":{}}, "invalid_api_response"),
    ([], "invalid_api_response"),
])
def test_safe_failure_categories(response, category, monkeypatch):
    provider = Ollama("mock")
    monkeypatch.setattr(provider, "_request", lambda *a, **kw: response)
    with pytest.raises(ProviderError) as error:
        provider.select("PRIVATE_QUESTION", plan())
    assert error.value.category == category
    diagnostic = provider.last_diagnostic.model_dump_json()
    assert "PRIVATE" not in diagnostic and provider.last_diagnostic.status == "failed"
    assert provider.last_diagnostic.elapsed_ms >= 0


def test_http_and_connectivity_diagnostics_are_distinct(monkeypatch):
    from urllib.error import HTTPError, URLError

    class Opener:
        failure = None
        def open(self, *args, **kwargs):
            raise self.failure
    opener = Opener()
    monkeypatch.setattr("retailpulse.agent.provider.build_opener", lambda *args: opener)
    for failure, category in (
        (HTTPError("http://secret.invalid", 500, "PRIVATE_TOKEN", {}, None), "http_error"),
        (URLError(ConnectionRefusedError(10061, "PRIVATE_TOKEN")), "connection_refused"),
        (URLError(TimeoutError("PRIVATE_TOKEN")), "timeout"),
        (URLError(OSError("PRIVATE_TOKEN")), "connection_error"),
    ):
        opener.failure = failure
        with pytest.raises(ProviderError) as error:
            Ollama("mock").models()
        assert error.value.category == category
        assert "PRIVATE" not in error.value.diagnostic.model_dump_json()
        assert error.value.diagnostic.http_status == (500 if category == "http_error" else None)


def test_complete_valid_json_still_cannot_change_scope(monkeypatch):
    provider = Ollama("mock")
    changed = plan().model_dump(mode="json")
    changed["call"]["arguments"]["limit"] = 99
    monkeypatch.setattr(provider, "_request", lambda *a,**kw: {"done":True,"message":{"content":json.dumps(changed)}, "eval_count":12})
    with pytest.raises(ProviderError, match="scope_mismatch"):
        provider.select("freshness", plan())
    assert provider.last_diagnostic.changed_fields == ["limit"]
    assert provider.last_diagnostic.generated_tokens == 12


def test_timeout_default_covers_local_model_loading_but_is_bounded():
    assert Ollama("mock").timeout_seconds == 30
    with pytest.raises(ValueError):
        Ollama("mock", timeout_seconds=31)
    assert ProviderError("PRIVATE_TOKEN").category == "provider_error"
