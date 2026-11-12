import pytest

from retail_analyst.settings import cost_usd

PRICES = """
models:
  cheap-model:
    input_per_million: 1.0
    output_per_million: 10.0
"""


@pytest.fixture
def prices_file(tmp_path):
    path = tmp_path / "pricing.yaml"
    path.write_text(PRICES)
    return path


def test_cost_is_tokens_times_the_per_million_price(prices_file):
    cost = cost_usd("cheap-model", input_tokens=2_000_000, output_tokens=500_000, path=prices_file)

    assert cost == pytest.approx(2 * 1.0 + 0.5 * 10.0)


def test_a_model_without_a_price_has_no_cost_rather_than_a_guess(prices_file):
    assert cost_usd("mystery", input_tokens=1000, output_tokens=1000, path=prices_file) is None
