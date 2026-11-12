import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_FALLBACK_MODEL = "gemini-3.7-flash"
DEFAULT_MAX_RETRIES = 3
TIMEOUT_SECONDS = 60
SAFE_MESSAGE = "The AI service is temporarily unavailable. Please try again later."
AUTH_MESSAGE = "The AI service rejected the configured credentials."

_models: dict[tuple, object] = {}


class LlmUnavailable(Exception):
    def __init__(self, user_message: str = SAFE_MESSAGE):
        super().__init__(user_message)
        self.user_message = user_message


def build_model():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    names = (
        os.environ.get("GEMINI_MODEL", DEFAULT_MODEL),
        os.environ.get("GEMINI_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL),
    )
    max_retries = int(os.environ.get("LLM_MAX_RETRIES", DEFAULT_MAX_RETRIES))
    key = (api_key, names, max_retries)
    if key not in _models:
        primary, fallback = (
            ChatGoogleGenerativeAI(
                model=name,
                google_api_key=api_key,
                max_retries=max_retries,
                timeout=TIMEOUT_SECONDS,
            )
            for name in names
        )
        _models[key] = primary.with_fallbacks([fallback])
    return _models[key]


def as_text(content) -> str:
    if isinstance(content, str):
        return content
    return "".join(part if isinstance(part, str) else part.get("text", "") for part in content)


def failure_message(error: Exception) -> str:
    code = getattr(error, "code", None) or getattr(error, "status_code", None)
    if code in (401, 403):
        return AUTH_MESSAGE
    return SAFE_MESSAGE


def generate(prompt: str, *, system: str | None = None, model=None, config=None) -> str:
    messages = [SystemMessage(system)] if system else []
    messages.append(HumanMessage(prompt))
    try:
        text = as_text((model or build_model()).invoke(messages, config).content).strip()
    except Exception as error:
        raise LlmUnavailable(failure_message(error)) from None
    if not text:
        raise LlmUnavailable() from None
    return text
