import os

import pytest

from retail_analyst.llm import generate

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="GEMINI_API_KEY absent"),
]


def test_live_generate_returns_text():
    assert generate("Reply with the single word: ok").strip()
