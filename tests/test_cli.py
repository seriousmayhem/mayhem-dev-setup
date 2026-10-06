"""End-to-end through `mayhem setup` with marker-file modules on the current OS."""

import sys

import pytest

from conftest import write
from mayhem import catalog, cli

WINDOWS = sys.platform == "win32"


def marker_module(root, name, requires="[]", fail_install=False):
    d = root / "modules" / name
    write(d / "module.toml", f"requires = {requires}\n")
    marker = d / "installed"
    if WINDOWS:
        write(d / "check.ps1", f"if (Test-Path '{marker}') {{ '1.0'; exit 0 }} else {{ exit 1 }}\n")
        write(d / "install.ps1", "exit 1\n" if fail_install else f"Set-Content '{marker}' x\n")
    else:
        write(d / "check.sh", f"[ -f '{marker}' ] && echo 1.0\n")
        write(d / "install.sh", "exit 1\n" if fail_install else f"touch '{marker}'\n")
    return marker


@pytest.fixture
def root(tmp_path, home, monkeypatch):
    r = tmp_path / "root"
    write(r / "profiles" / "p.toml", 'modules = ["b"]\n')
    write(r / "versions.toml", 'a = "1.0"\nb = "2.0"\n')
    monkeypatch.setattr(catalog, "default_roots", lambda: [r])
    return r


def test_converges_then_reports_no_changes(root, capsys):
    a = marker_module(root, "a")
    b = marker_module(root, "b", requires='["a"]')

    assert cli.main(["setup", "--profile", "p", "--yes", "--expect-no-changes"]) == cli.EXIT_CHANGED
    assert a.exists() and b.exists()
    out = capsys.readouterr().out
    assert out.index("  a ") < out.index("  b ")
    assert "2 changed" in out

    assert cli.main(["setup", "--profile", "p", "--yes", "--expect-no-changes"]) == 0
    out = capsys.readouterr().out
    assert "0 changed, 2 already converged" in out
    assert "(pin 2.0, drift)" in out  # check printed 1.0


def test_dry_run_installs_nothing(root):
    a = marker_module(root, "a")
    marker_module(root, "b", requires='["a"]')
    assert cli.main(["setup", "--profile", "p", "--yes", "--dry-run"]) == 0
    assert not a.exists()


def test_failed_install_stops_and_points_at_log(root, capsys):
    marker_module(root, "a", fail_install=True)
    b = marker_module(root, "b", requires='["a"]')
    assert cli.main(["setup", "--profile", "p", "--yes"]) == cli.EXIT_FAILED
    assert not b.exists()
    assert "a.log" in capsys.readouterr().err


def test_secrets_reach_scripts_and_file_is_deleted(root, tmp_path, monkeypatch):
    monkeypatch.setenv("JOIN_TOKEN", "")  # so the value setup loads is undone after the test
    seen = tmp_path / "seen"
    d = root / "modules" / "b"
    write(d / "module.toml", "")
    if WINDOWS:
        write(d / "check.ps1", "exit 1\n")
        write(d / "install.ps1", f"Set-Content '{seen}' $env:JOIN_TOKEN\nexit 1\n")
    else:
        write(d / "check.sh", "exit 1\n")
        write(d / "install.sh", f"printf %s \"$JOIN_TOKEN\" > '{seen}'; exit 1\n")
    secrets = write(tmp_path / "join.env", "JOIN_TOKEN=s3cret\n")
    secrets.chmod(0o600)

    assert cli.main(["setup", "--profile", "p", "--yes", "--secrets-file", str(secrets)]) == cli.EXIT_FAILED
    assert seen.read_text().strip() == "s3cret"
    assert not secrets.exists()  # deleted even though setup failed


def test_no_terminal_and_no_profile_is_a_usage_error(root, monkeypatch):
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert cli.main(["setup"]) == cli.EXIT_USAGE


@pytest.mark.parametrize(("os_name", "nvidia", "expected"), [
    ("windows", True, ["human"]),
    ("linux", False, ["human"]),
    ("linux", True, ["worker", "inference"]),
])
def test_default_profiles(os_name, nvidia, expected):
    assert cli.default_profiles(os_name, nvidia, {"human", "worker", "inference"}) == expected


def test_default_profiles_drop_ones_not_on_this_machine():
    assert cli.default_profiles("linux", True, {"human"}) == []
