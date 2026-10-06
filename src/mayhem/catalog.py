"""Profiles, modules and pins, read from every root on the search path.

A root is a checkout with any of `profiles/`, `modules/` and `versions.toml`. The public
setup repo is always first; the private fleet checkout, when present, is layered over it.
"""

import os
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class CatalogError(Exception):
    pass


def current_os() -> str:
    return "windows" if sys.platform == "win32" else "linux"


def mayhem_home() -> Path:
    return Path(os.environ.get("MAYHEM_HOME") or Path.home() / ".mayhem")


def default_roots() -> list[Path]:
    roots = [REPO_ROOT]
    fleet = mayhem_home() / "fleet"
    if fleet.is_dir():
        roots.append(fleet)
    return roots


@dataclass
class Module:
    name: str
    path: Path
    description: str = ""
    os: list[str] = field(default_factory=lambda: ["windows", "linux"])
    requires: list[str] = field(default_factory=list)
    # "exact": the version must equal the pin. "floor": anything at or above it.
    pin_kind: str = "exact"

    def script(self, verb: str, os_name: str) -> Path:
        return self.path / f"{verb}.{'ps1' if os_name == 'windows' else 'sh'}"


@dataclass
class Profile:
    name: str
    description: str = ""
    include: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)


@dataclass
class Catalog:
    modules: dict[str, Module]
    profiles: dict[str, Profile]
    pins: dict[str, str]

    @classmethod
    def load(cls, roots: list[Path] | None = None) -> "Catalog":
        modules: dict[str, Module] = {}
        profiles: dict[str, Profile] = {}
        pins: dict[str, str] = {}
        for root in roots or default_roots():
            for path in sorted((root / "modules").glob("*/module.toml")):
                # _lib and friends hold shared helpers, not modules.
                if path.parent.name.startswith("_"):
                    continue
                data = _read_toml(path)
                modules[path.parent.name] = Module(
                    name=path.parent.name,
                    path=path.parent,
                    description=data.get("description", ""),
                    os=data.get("os", ["windows", "linux"]),
                    requires=data.get("requires", []),
                    pin_kind=data.get("pin", "exact"),
                )
            for path in sorted((root / "profiles").glob("*.toml")):
                data = _read_toml(path)
                profiles[path.stem] = Profile(
                    name=path.stem,
                    description=data.get("description", ""),
                    include=data.get("include", []),
                    modules=data.get("modules", []),
                )
            if (root / "versions.toml").is_file():
                pins.update(load_pins(root / "versions.toml"))
        return cls(modules, profiles, pins)

    def profile_modules(self, names: list[str]) -> list[str]:
        """Module names from the profiles, includes expanded, first mention wins."""
        seen: list[str] = []
        visiting: list[str] = []

        def visit(name: str) -> None:
            if name not in self.profiles:
                raise CatalogError(f"unknown profile {name!r} (have: {', '.join(sorted(self.profiles))})")
            if name in visiting:
                raise CatalogError("profile include cycle: " + " -> ".join([*visiting, name]))
            visiting.append(name)
            profile = self.profiles[name]
            for include in profile.include:
                visit(include)
            for module in profile.modules:
                if module not in seen:
                    seen.append(module)
            visiting.pop()

        for name in names:
            visit(name)
        return seen

    def plan(self, wanted: list[str], os_name: str, skip: set[str] = frozenset()) -> list[Module]:
        """Wanted modules plus their requirements, requirements first.

        Modules not built for os_name are dropped, unless something needs them.
        """
        order: list[Module] = []
        done: set[str] = set()
        stack: list[str] = []

        def visit(name: str, needed_by: str | None) -> None:
            if name in done:
                return
            if name in stack:
                raise CatalogError("module requires cycle: " + " -> ".join([*stack, name]))
            module = self.modules.get(name)
            if module is None:
                where = f" (required by {needed_by})" if needed_by else ""
                raise CatalogError(f"unknown module {name!r}{where}")
            if os_name not in module.os:
                if needed_by:
                    raise CatalogError(f"{needed_by} requires {name}, which doesn't support {os_name}")
                done.add(name)
                return
            stack.append(name)
            for dep in module.requires:
                visit(dep, name)
            stack.pop()
            done.add(name)
            if name not in skip:
                order.append(module)

        for name in wanted:
            visit(name, None)
        return order


def load_pins(path: Path) -> dict[str, str]:
    data = _read_toml(path)
    bad = [k for k, v in data.items() if not isinstance(v, str)]
    if bad:
        raise CatalogError(f"{path}: pins must be strings: {', '.join(bad)}")
    return data


def _read_toml(path: Path) -> dict:
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise CatalogError(f"{path}: {e}") from e
