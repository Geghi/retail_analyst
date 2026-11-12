from retail_analyst.cli import main

GOOD_ENV = {
    "GEMINI_API_KEY": "key",
    "GEMINI_MODEL": "main-model",
    "GEMINI_FALLBACK_MODEL": "fallback-model",
    "GCP_PROJECT_ID": "project",
    "DATABASE_URL": "postgresql://analyst:analyst@localhost:5432/analyst",
}


def run(argv, env):
    shown = []
    code = main(argv, env=env, read=lambda prompt: "exit", write=shown.append)
    return code, "\n".join(shown)


def test_an_unknown_user_is_rejected_with_the_list_of_valid_users():
    code, output = run(["--user", "mallory"], GOOD_ENV)

    assert code == 2
    assert "mallory" in output
    assert "alice" in output and "bob" in output and "carol" in output


def test_a_missing_gemini_key_is_named_in_a_plain_message():
    env = {key: value for key, value in GOOD_ENV.items() if key != "GEMINI_API_KEY"}

    code, output = run(["--user", "alice"], env)

    assert code == 1
    assert "GEMINI_API_KEY" in output
    assert "Traceback" not in output


def test_a_credentials_file_that_does_not_exist_is_reported(tmp_path):
    env = {**GOOD_ENV, "GOOGLE_APPLICATION_CREDENTIALS": str(tmp_path / "missing.json")}

    code, output = run(["--user", "alice"], env)

    assert code == 1
    assert "GOOGLE_APPLICATION_CREDENTIALS" in output
    assert "missing.json" in output


def test_an_unreachable_database_tells_how_to_start_it():
    env = {**GOOD_ENV, "DATABASE_URL": "postgresql://analyst:analyst@localhost:1/analyst"}

    code, output = run(["--user", "alice"], env)

    assert code == 1
    assert "docker compose up -d db" in output


def test_a_missing_fallback_model_is_named_in_a_plain_message():
    env = {key: value for key, value in GOOD_ENV.items() if key != "GEMINI_FALLBACK_MODEL"}

    code, output = run(["--user", "alice"], env)

    assert code == 1
    assert "GEMINI_FALLBACK_MODEL" in output
