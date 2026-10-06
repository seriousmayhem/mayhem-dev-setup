import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def git_bash() -> str | None:
    """Git's bash on Windows (plain `bash` may be WSL's), `bash` elsewhere."""
    if sys.platform == "win32":
        if git := shutil.which("git"):
            for candidate in (Path(git).parents[1] / "bin" / "bash.exe", Path(git).parents[2] / "bin" / "bash.exe"):
                if candidate.is_file():
                    return str(candidate)
        return None
    return shutil.which("bash")


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Point every per-user path the CLI and scripts touch at a temp dir."""
    h = tmp_path / "home"
    h.mkdir()
    monkeypatch.setenv("MAYHEM_HOME", str(h / ".mayhem"))
    return h
