import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import ai724  # noqa: E402


def test_env_path_prefers_env_var(tmp_path, monkeypatch):
    f = tmp_path / "x.env"
    f.write_text("AI724_API_KEY=k\n", encoding="utf-8")
    monkeypatch.setenv("AI724_ENV_FILE", str(f))
    assert ai724.env_path() == f


def test_env_path_falls_back_to_cwd_secrets(tmp_path, monkeypatch):
    monkeypatch.delenv("AI724_ENV_FILE", raising=False)
    (tmp_path / ".secrets").mkdir()
    f = tmp_path / ".secrets" / "ai724.env"
    f.write_text("AI724_API_KEY=k\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert ai724.env_path() == f


def test_env_path_missing_gives_helpful_error(tmp_path, monkeypatch):
    monkeypatch.delenv("AI724_ENV_FILE", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError, match="AI724_ENV_FILE"):
        ai724.env_path()


def test_env_parsing_ignores_comments(tmp_path):
    f = tmp_path / "e.env"
    f.write_text("# c\nAI724_API_KEY = abc\nAI724_REFRESH_TOKEN=x=y\n", encoding="utf-8")
    assert ai724._env(f) == {"AI724_API_KEY": "abc", "AI724_REFRESH_TOKEN": "x=y"}
