import os
import random
import time

from google import genai
from google.genai import errors, types

DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_FALLBACK_MODEL = "gemini-3.7-flash"
AUTH_CODES = {401, 403}
SAFE_MESSAGE = "The AI service is temporarily unavailable. Please try again later."
AUTH_MESSAGE = "The AI service rejected the configured credentials."

_clients: dict[str, genai.Client] = {}


class LlmUnavailable(Exception):
    def __init__(self, user_message: str = SAFE_MESSAGE):
        super().__init__(user_message)
        self.user_message = user_message


def default_models() -> list[str]:
    return [
        os.environ.get("GEMINI_MODEL", DEFAULT_MODEL),
        os.environ.get("GEMINI_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL),
    ]


def default_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if api_key not in _clients:
        _clients[api_key] = genai.Client(api_key=api_key)
    return _clients[api_key]


def is_transient(error: errors.APIError) -> bool:
    return isinstance(error, errors.ServerError) or error.code == 429


def backoff(attempt: int) -> float:
    return 2**attempt + random.uniform(0, 1)


def call_with_retries(client, model, prompt, config, max_retries, sleep) -> str | None:
    for attempt in range(max_retries + 1):
        try:
            return client.models.generate_content(model=model, contents=prompt, config=config).text
        except errors.APIError as error:
            if error.code in AUTH_CODES:
                raise LlmUnavailable(AUTH_MESSAGE) from None
            if not is_transient(error):
                return None
            if attempt < max_retries:
                sleep(backoff(attempt))
    return None


def generate(
    prompt: str,
    *,
    system: str | None = None,
    client=None,
    models: list[str] | None = None,
    max_retries: int = 3,
    sleep=time.sleep,
) -> str:
    client = client or default_client()
    config = types.GenerateContentConfig(system_instruction=system)
    for model in models or default_models():
        text = call_with_retries(client, model, prompt, config, max_retries, sleep)
        if text is not None:
            return text
    raise LlmUnavailable() from None
