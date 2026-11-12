import pytest

from retail_analyst.guardrails import UserScope
from retail_analyst.settings import UnknownUser, list_users, load_persona, load_scope

USERS = """
users:
  dana:
    name: Dana
    categories: [Jeans, Sweaters]
  eli:
    name: Eli
    categories: [Suits & Sport Coats]
"""


@pytest.fixture
def users_file(tmp_path):
    path = tmp_path / "users.yaml"
    path.write_text(USERS)
    return path


def test_known_user_gets_exactly_their_categories(users_file):
    assert load_scope("dana", users_file) == UserScope("dana", frozenset({"Jeans", "Sweaters"}))


def test_unknown_user_raises_without_leaking_other_users(users_file):
    with pytest.raises(UnknownUser) as raised:
        load_scope("mallory", users_file)
    message = str(raised.value)
    assert "mallory" in message
    assert "dana" not in message and "eli" not in message and "Jeans" not in message


def test_list_users(users_file):
    assert list_users(users_file) == ["dana", "eli"]


@pytest.mark.parametrize(
    "content",
    ["users: [unclosed", "just text", "users: {a: {name: A}}", "users: {a: {categories: []}}"],
)
def test_malformed_users_file_raises_a_clear_error(tmp_path, content):
    path = tmp_path / "users.yaml"
    path.write_text(content)
    with pytest.raises(ValueError, match="users"):
        load_scope("a", path)


def test_config_dir_env_is_read_at_call_time(tmp_path, monkeypatch, users_file):
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))
    assert list_users() == ["dana", "eli"]


def test_shipped_config_defines_the_three_executives(monkeypatch):
    monkeypatch.delenv("CONFIG_DIR", raising=False)
    assert list_users() == ["alice", "bob", "carol"]
    assert load_scope("bob").allowed_categories == frozenset(
        {"Outerwear & Coats", "Suits & Sport Coats"}
    )


def test_persona_edits_are_visible_on_the_next_call(tmp_path):
    path = tmp_path / "persona.md"
    path.write_text("formal")
    assert load_persona(path) == "formal"
    path.write_text("casual")
    assert load_persona(path) == "casual"


def test_shipped_persona_is_not_empty(monkeypatch):
    monkeypatch.delenv("CONFIG_DIR", raising=False)
    assert "action items" in load_persona()
