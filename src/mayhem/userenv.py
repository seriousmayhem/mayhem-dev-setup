"""Inputs that never live in the repo: the secrets file and the per-person user.toml."""

import json
import os
import subprocess
import tomllib
from pathlib import Path

from .catalog import mayhem_home

USER_FIELDS = {"name": "Your name (for git commits)", "email": "Your email (for git commits)"}


class SecretsError(Exception):
    pass


def read_secrets(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise SecretsError(f"secrets file {path} not found")
    # Windows has no POSIX modes; NTFS ACLs on the user profile do the job there.
    if os.name == "posix" and path.stat().st_mode & 0o077:
        raise SecretsError(f"{path} must be readable by its owner only (chmod 600 {path})")
    secrets = {}
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep or not key.strip().isidentifier():
            # Never echo the line: it may be a secret.
            raise SecretsError(f"{path}:{n}: expected KEY=value")
        secrets[key.strip()] = value.strip()
    return secrets


def user_toml() -> Path:
    return mayhem_home() / "user.toml"


def load_user(prompt) -> dict[str, str]:
    """Values from user.toml; missing ones are asked for when prompt is given, then saved."""
    path = user_toml()
    values = tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    missing = [k for k in USER_FIELDS if not values.get(k)]
    if missing and prompt:
        for key in missing:
            answer = prompt(USER_FIELDS[key], _git_default(key))
            if answer:
                values[key] = answer
        path.parent.mkdir(parents=True, exist_ok=True)
        # json.dumps output is a valid TOML basic string.
        path.write_text("".join(f"{k} = {json.dumps(v)}\n" for k, v in values.items()), encoding="utf-8")
    return values


def user_env(values: dict[str, str]) -> dict[str, str]:
    return {f"MAYHEM_USER_{k.upper()}": v for k, v in values.items() if isinstance(v, str) and v}


def _git_default(key: str) -> str:
    try:
        out = subprocess.run(["git", "config", "--global", f"user.{key}"], capture_output=True, text=True)
    except FileNotFoundError:
        return ""
    return out.stdout.strip()
