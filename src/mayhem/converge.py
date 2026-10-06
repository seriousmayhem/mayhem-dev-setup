"""Runs module scripts: check, then install and check again if needed.

The contract a module script follows: `check` exits 0 when converged and prints the
installed version on stdout; `install` is idempotent. Both run fine by hand.
"""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .catalog import REPO_ROOT, Catalog, Module, mayhem_home


@dataclass
class Result:
    module: str
    status: str  # ok | installed | would-install | missing | failed
    version: str = ""
    pin: str = ""
    drift: bool = False
    log: Path | None = None


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", version))


def is_drift(module: Module, pin: str, version: str) -> bool:
    if not pin or not version:
        return False
    if module.pin_kind == "floor":
        return version_key(version) < version_key(pin)
    return version != pin


def bin_dir() -> Path:
    """Where modules put binaries: uv's tool bin dir, which the `path` module puts on PATH."""
    if uv := shutil.which("uv"):
        out = subprocess.run([uv, "tool", "dir", "--bin"], capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    return Path.home() / ".local" / "bin"


def script_env(module: Module, catalog: Catalog) -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        MAYHEM_HOME=str(mayhem_home()),
        MAYHEM_BIN=str(bin_dir()),
        MAYHEM_LIB=str(REPO_ROOT / "modules" / "_lib"),
        MAYHEM_MODULE_DIR=str(module.path),
    )
    if pin := catalog.pins.get(module.name):
        env["MAYHEM_VERSION"] = pin
    return env


def command(script: Path) -> list[str]:
    if script.suffix == ".ps1":
        # Windows PowerShell 5.1 is the one shell every Windows machine has.
        return ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script)]
    return ["bash", str(script)]


class Runner:
    def __init__(self, catalog: Catalog, os_name: str, log_dir: Path | None = None):
        self.catalog = catalog
        self.os_name = os_name
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.log_dir = log_dir or mayhem_home() / "logs" / stamp

    def _run(self, module: Module, verb: str, log: Path) -> tuple[int, str]:
        script = module.script(verb, self.os_name)
        if not script.is_file():
            raise FileNotFoundError(f"{module.name}: missing {script.name}")
        proc = subprocess.run(
            command(script), env=script_env(module, self.catalog), capture_output=True, text=True,
            encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
        )
        with log.open("a", encoding="utf-8") as f:
            f.write(f"$ {verb} (exit {proc.returncode})\n{proc.stdout}{proc.stderr}\n")
        lines = proc.stdout.strip().splitlines()
        return proc.returncode, lines[-1].strip() if lines else ""

    def _result(self, module: Module, status: str, version: str, log: Path) -> Result:
        pin = self.catalog.pins.get(module.name, "")
        return Result(module.name, status, version, pin, is_drift(module, pin, version), log)

    def converge(self, module: Module, dry_run: bool = False) -> Result:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        log = self.log_dir / f"{module.name}.log"
        rc, version = self._run(module, "check", log)
        if rc == 0:
            return self._result(module, "ok", version, log)
        if dry_run:
            return self._result(module, "would-install", version, log)
        rc, _ = self._run(module, "install", log)
        if rc != 0:
            return self._result(module, "failed", "", log)
        rc, version = self._run(module, "check", log)
        return self._result(module, "installed" if rc == 0 else "failed", version, log)

    def check(self, module: Module) -> Result:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        log = self.log_dir / f"{module.name}.log"
        rc, version = self._run(module, "check", log)
        return self._result(module, "ok" if rc == 0 else "missing", version, log)
