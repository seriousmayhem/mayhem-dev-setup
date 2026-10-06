import os

import pytest

from conftest import write
from mayhem.userenv import SecretsError, load_user, read_secrets, user_env, user_toml


def secrets_file(tmp_path, text):
    path = write(tmp_path / "join.env", text)
    path.chmod(0o600)
    return path


def test_secrets_parse_skipping_comments_and_blanks(tmp_path):
    path = secrets_file(tmp_path, "# runner\nGH_TOKEN=abc=def\n\n  OPENROUTER_KEY = xyz \n")
    assert read_secrets(path) == {"GH_TOKEN": "abc=def", "OPENROUTER_KEY": "xyz"}


def test_malformed_secret_line_is_not_echoed(tmp_path):
    path = secrets_file(tmp_path, "ghp_supersecretvalue\n")
    with pytest.raises(SecretsError) as e:
        read_secrets(path)
    assert "supersecret" not in str(e.value)
    assert ":1:" in str(e.value)


@pytest.mark.skipif(os.name != "posix", reason="POSIX modes only")
def test_group_readable_secrets_file_is_refused(tmp_path):
    path = secrets_file(tmp_path, "A=1\n")
    path.chmod(0o640)
    with pytest.raises(SecretsError, match="chmod 600"):
        read_secrets(path)


def test_user_values_are_prompted_once_then_saved(home):
    asked = []

    def prompt(label, default):
        asked.append(label)
        return 'Ada "Al" Lovelace' if "name" in label else "ada@example.com"

    values = load_user(prompt)
    assert values == {"name": 'Ada "Al" Lovelace', "email": "ada@example.com"}
    assert len(asked) == 2
    assert load_user(prompt) == values  # read back from user.toml, no new prompts
    assert len(asked) == 2
    assert user_env(values) == {"MAYHEM_USER_NAME": 'Ada "Al" Lovelace', "MAYHEM_USER_EMAIL": "ada@example.com"}


def test_unattended_run_neither_prompts_nor_writes(home):
    assert load_user(None) == {}
    assert not user_toml().exists()
