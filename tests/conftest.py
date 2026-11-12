import pytest


def pytest_collection_modifyitems(config, items):
    """Live scenarios spend model and warehouse quota: they run only when asked for by name."""
    if "acceptance" in (config.getoption("markexpr") or ""):
        return
    skip = pytest.mark.skip(reason="live scenarios: pytest tests/acceptance -m acceptance")
    for item in items:
        if "acceptance" in item.keywords:
            item.add_marker(skip)
