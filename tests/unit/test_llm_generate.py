import pytest
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models.fake_chat_models import (
    FakeListChatModel,
    GenericFakeChatModel,
)
from langchain_core.messages import AIMessage

from retail_analyst.llm import LlmUnavailable, build_model, generate

SECRET = "AIza-secret-key"


class Boom(FakeListChatModel):
    def _call(self, *args, **kwargs):
        raise RuntimeError(f"boom key={SECRET}")


class Seen(BaseCallbackHandler):
    def __init__(self):
        self.started = 0

    def on_chat_model_start(self, *args, **kwargs):
        self.started += 1


def reply(content):
    return GenericFakeChatModel(messages=iter([AIMessage(content=content)]))


def test_success_returns_text():
    assert (
        generate("hi", system="be brief", model=FakeListChatModel(responses=["answer"])) == "answer"
    )


def test_list_of_parts_is_joined_as_text():
    parts = [{"type": "text", "text": "ab"}, {"type": "text", "text": "cd"}]
    assert generate("hi", model=reply(parts)) == "abcd"


def test_failing_model_raises_without_leaking_key():
    with pytest.raises(LlmUnavailable) as raised:
        generate("hi", model=Boom(responses=["x"]))
    error = raised.value
    assert error.user_message and str(error) == error.user_message
    assert SECRET not in str(error) and SECRET not in repr(error)
    assert error.__cause__ is None and error.__suppress_context__


@pytest.mark.parametrize("content", ["", "   ", []])
def test_empty_reply_raises(content):
    with pytest.raises(LlmUnavailable):
        generate("hi", model=reply(content))


def test_config_reaches_the_model_callbacks():
    handler = Seen()
    generate("hi", model=FakeListChatModel(responses=["ok"]), config={"callbacks": [handler]})
    assert handler.started == 1


def test_build_model_uses_environment_models(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", SECRET)
    monkeypatch.setenv("GEMINI_MODEL", "env-main")
    monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "env-fallback")
    model = build_model()
    assert model.runnable.model == "env-main"
    assert [f.model for f in model.fallbacks] == ["env-fallback"]


def test_build_model_defaults(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", SECRET)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_FALLBACK_MODEL", raising=False)
    model = build_model()
    assert model.runnable.model == "gemini-3.6-flash"
    assert [f.model for f in model.fallbacks] == ["gemini-3.5-flash"]


def test_build_model_is_cached(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", SECRET)
    assert build_model() is build_model()


def test_build_model_has_a_short_default_timeout_and_few_retries(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", SECRET)
    monkeypatch.delenv("LLM_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("LLM_MAX_RETRIES", raising=False)
    model = build_model()
    assert model.runnable.timeout == 20
    assert model.runnable.max_retries == 2


def test_build_model_timeout_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", SECRET)
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "7")
    model = build_model()
    assert model.runnable.timeout == 7
    assert model.fallbacks[0].timeout == 7


class QuotaExceeded(FakeListChatModel):
    def _call(self, *args, **kwargs):
        error = RuntimeError("429 RESOURCE_EXHAUSTED daily limit")
        error.code = 429
        raise error


def test_a_quota_limit_says_the_daily_limit_is_reached_not_that_the_service_is_down():
    with pytest.raises(LlmUnavailable) as raised:
        generate("hi", model=QuotaExceeded(responses=["x"]))

    assert "limit" in raised.value.user_message.lower()
    assert "temporarily unavailable" not in raised.value.user_message


class RealRateLimit(FakeListChatModel):
    def _call(self, *args, **kwargs):
        from langchain_google_genai.chat_models import GoogleRateLimitError

        raise GoogleRateLimitError("Error calling model (RESOURCE_EXHAUSTED): 429 quota exceeded")


def test_the_real_gemini_rate_limit_error_is_reported_as_a_usage_limit():
    with pytest.raises(LlmUnavailable) as raised:
        generate("hi", model=RealRateLimit(responses=["x"]))

    assert "limit" in raised.value.user_message.lower()
