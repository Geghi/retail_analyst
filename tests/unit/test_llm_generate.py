from types import SimpleNamespace

import pytest
from google.genai import errors

from retail_analyst.llm import LlmUnavailable, generate

SECRET = "AIza-secret-key"


def api_error(code):
    cls = errors.ServerError if code >= 500 else errors.ClientError
    return cls(code, {"error": {"message": f"boom key={SECRET}", "status": "X"}})


class FakeClient:
    def __init__(self, script):
        self.script = script
        self.calls = []
        self.models = self

    def generate_content(self, *, model, contents, config):
        self.calls.append((model, contents, config))
        outcome = self.script[model].pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(text=outcome)


def run(script, **kwargs):
    client = FakeClient(script)
    sleeps = []
    kwargs.setdefault("models", ["m1", "m2"])
    result = generate("hi", client=client, sleep=sleeps.append, **kwargs)
    return result, client, sleeps


def test_success_returns_text_and_passes_prompt_and_system():
    result, client, _ = run({"m1": ["answer"]}, system="be brief")
    model, contents, config = client.calls[0]
    assert (result, model, contents) == ("answer", "m1", "hi")
    assert config.system_instruction == "be brief"


def test_transient_errors_retry_with_growing_backoff_on_same_model():
    result, client, sleeps = run({"m1": [api_error(503), api_error(429), "ok"]})
    assert result == "ok"
    assert [c[0] for c in client.calls] == ["m1"] * 3
    assert len(sleeps) == 2 and 1 <= sleeps[0] < sleeps[1]


def test_falls_back_to_next_model_after_retries_exhausted():
    script = {"m1": [api_error(500)] * 4, "m2": ["fallback"]}
    result, client, sleeps = run(script, max_retries=3)
    assert result == "fallback"
    assert [c[0] for c in client.calls] == ["m1"] * 4 + ["m2"]
    assert len(sleeps) == 3


def test_404_moves_to_next_model_without_retry():
    result, client, sleeps = run({"m1": [api_error(404)], "m2": ["ok"]})
    assert (result, sleeps) == ("ok", [])
    assert [c[0] for c in client.calls] == ["m1", "m2"]


@pytest.mark.parametrize("code", [401, 403])
def test_auth_error_raises_at_once(code):
    client = FakeClient({"m1": [api_error(code)], "m2": ["never"]})
    with pytest.raises(LlmUnavailable):
        generate("hi", client=client, models=["m1", "m2"], sleep=lambda s: None)
    assert len(client.calls) == 1


def test_exhaustion_raises_without_leaking_key():
    script = {"m1": [api_error(404)], "m2": [api_error(503)] * 4}
    with pytest.raises(LlmUnavailable) as raised:
        run(script)
    error = raised.value
    assert error.user_message
    assert SECRET not in str(error) and SECRET not in error.user_message
    assert SECRET not in repr(error.args)
    assert error.__cause__ is None and error.__suppress_context__


def test_default_models_read_from_environment_at_call_time(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "env-main")
    monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "env-fallback")
    client = FakeClient({"env-main": [api_error(404)], "env-fallback": ["ok"]})
    assert generate("hi", client=client, sleep=lambda s: None) == "ok"
    assert [c[0] for c in client.calls] == ["env-main", "env-fallback"]
