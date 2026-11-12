import pytest

from retail_analyst.knowledge import Trio, load_trios

VALID = "id: a\nquestion: Why?\nqueries:\n  - SELECT 1\nreport: Because.\n"


def test_loads_trios_from_a_directory_sorted_by_file(tmp_path):
    (tmp_path / "b.yaml").write_text(VALID.replace("id: a", "id: b"))
    (tmp_path / "a.yaml").write_text(VALID)
    assert load_trios(tmp_path) == [
        Trio(id="a", question="Why?", queries=["SELECT 1"], report="Because."),
        Trio(id="b", question="Why?", queries=["SELECT 1"], report="Because."),
    ]


def test_golden_dir_environment_variable_is_read_at_call_time(tmp_path, monkeypatch):
    (tmp_path / "a.yaml").write_text(VALID)
    monkeypatch.setenv("GOLDEN_DIR", str(tmp_path))
    assert [t.id for t in load_trios()] == ["a"]


def test_default_directory_holds_the_shipped_trios(monkeypatch):
    monkeypatch.delenv("GOLDEN_DIR", raising=False)
    assert len(load_trios()) >= 5


@pytest.mark.parametrize(
    "content",
    [
        "id: a\nquestion: Why?\n",
        "- just\n- a list\n",
        "id: [unclosed\n",
        VALID.replace("  - SELECT 1", "  - 3"),
    ],
)
def test_malformed_file_raises_an_error_naming_the_file(tmp_path, content):
    (tmp_path / "broken.yaml").write_text(content)
    with pytest.raises(ValueError, match="broken.yaml"):
        load_trios(tmp_path)
