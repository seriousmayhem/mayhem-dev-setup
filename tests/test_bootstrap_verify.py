"""The bootstrap refuses any ref that isn't a v* tag signed by the embedded release key."""

import os
import shutil
import subprocess
import sys

import pytest

from conftest import REPO, git_bash, write

BASH = git_bash()
PWSH = shutil.which("pwsh") or (shutil.which("powershell") if sys.platform == "win32" else None)


def git(cwd, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "tag.gpgSign=false", *args],
        cwd=cwd, check=True, capture_output=True,
    )


@pytest.fixture(scope="module")
def origin(tmp_path_factory):
    """A release repo with a stub CLI: v0.0.1 unsigned, v0.0.2 signed by a key that isn't allowed."""
    tmp = tmp_path_factory.mktemp("origin")
    repo = tmp / "repo"
    write(repo / "pyproject.toml", '[project]\nname = "mayhem"\nversion = "0"\n[project.scripts]\nmayhem = "mayhem:main"\n'
          '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n')
    write(repo / "src" / "mayhem" / "__init__.py", "import sys\ndef main(): print('STUB', *sys.argv[1:])\n")
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "stub")
    git(repo, "tag", "-a", "v0.0.1", "-m", "unsigned")
    key = tmp / "intruder"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
    git(repo, "-c", "gpg.format=ssh", "-c", f"user.signingkey={key.as_posix()}", "tag", "-s", "v0.0.2", "-m", "intruder")
    return repo


def env_for(origin, tmp_path, ref):
    env = dict(os.environ)
    env.update(
        MAYHEM_REPO_URL=origin.as_uri(),
        MAYHEM_HOME=(tmp_path / "home").as_posix(),
        UV_TOOL_DIR=(tmp_path / "uv-tools").as_posix(),
        UV_TOOL_BIN_DIR=(tmp_path / "uv-bin").as_posix(),
    )
    if ref:
        env["MAYHEM_REF"] = ref
    return env


def run_sh(origin, tmp_path, ref, *args):
    return subprocess.run([BASH, str(REPO / "bootstrap.sh"), *args], env=env_for(origin, tmp_path, ref),
                          capture_output=True, text=True, stdin=subprocess.DEVNULL)


def run_ps(origin, tmp_path, ref, *args):
    script = f"& ([scriptblock]::Create((Get-Content -Raw '{REPO / 'bootstrap.ps1'}'))) {' '.join(args)}"
    return subprocess.run([PWSH, "-NoProfile", "-Command", script], env=env_for(origin, tmp_path, ref),
                          capture_output=True, text=True, stdin=subprocess.DEVNULL)


RUNNERS = [
    pytest.param(run_sh, marks=pytest.mark.skipif(not BASH, reason="no bash")),
    # The .ps1 only targets Windows; elsewhere it would need winget for its final step.
    pytest.param(run_ps, marks=pytest.mark.skipif(not PWSH or sys.platform != "win32", reason="Windows only")),
]


@pytest.mark.parametrize("run", RUNNERS)
@pytest.mark.parametrize("ref", [None, "v0.0.1", "v0.0.2", "main"])
def test_refused(run, ref, origin, tmp_path):
    # None: the newest tag (v0.0.2, wrong key) is what an unpinned bootstrap picks.
    proc = run(origin, tmp_path, ref)
    out = proc.stdout + proc.stderr
    assert "not a release tag signed by an allowed key" in out
    assert "STUB" not in out
    if run is run_sh:
        assert proc.returncode != 0


@pytest.mark.parametrize("run", RUNNERS)
def test_allow_unsigned_converges_with_warning(run, origin, tmp_path):
    proc = run(origin, tmp_path, "main", "--allow-unsigned", "--profile", "base")
    out = proc.stdout + proc.stderr
    assert "WARNING: converging unsigned ref main" in out
    assert "STUB setup --profile base" in out
