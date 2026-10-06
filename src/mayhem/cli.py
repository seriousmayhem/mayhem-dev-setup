"""mayhem: orders modules, runs their scripts, logs and reports. Nothing else."""

import argparse
import json
import os
import sys
from pathlib import Path

from . import probe as probe_mod
from .catalog import Catalog, CatalogError, current_os
from .converge import Result, Runner
from .userenv import SecretsError, load_user, read_secrets, user_env

EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_CHANGED = 3  # --expect-no-changes saw a change


def default_profiles(os_name: str, has_nvidia: bool, available: set[str]) -> list[str]:
    if os_name == "linux" and has_nvidia:
        wanted = ["worker", "inference"]
    else:
        wanted = ["human"]
    return [p for p in wanted if p in available]


def interactive(args) -> bool:
    return not args.yes and sys.stdin.isatty()


def pick_profiles(catalog: Catalog, preselected: list[str]) -> list[str]:
    import questionary

    choices = [
        questionary.Choice(f"{p.name}: {p.description}" if p.description else p.name, p.name, checked=p.name in preselected)
        for p in sorted(catalog.profiles.values(), key=lambda p: p.name)
    ]
    picked = questionary.checkbox("Profiles to set up on this machine", choices=choices).ask()
    if picked is None:  # Ctrl-C
        raise KeyboardInterrupt
    return picked


def ask(label: str, default: str) -> str:
    import questionary

    return (questionary.text(label, default=default).ask() or "").strip()


def print_table(results: list[Result], width: int = 0) -> None:
    width = width or max((len(r.module) for r in results), default=6)
    for r in results:
        pin = f"  (pin {r.pin}{', drift' if r.drift else ''})" if r.pin else ""
        print(f"  {r.module:<{width}}  {r.status:<13}  {r.version}{pin}")


def cmd_setup(args) -> int:
    catalog = Catalog.load()
    os_name = current_os()

    if args.profile:
        profiles = [p.strip() for p in args.profile.split(",") if p.strip()]
    else:
        preselected = default_profiles(os_name, bool(probe_mod.gpus()), set(catalog.profiles))
        if interactive(args):
            profiles = pick_profiles(catalog, preselected)
        elif args.yes and preselected:
            profiles = preselected
        else:
            print("error: no terminal to pick profiles; pass --profile NAME[,NAME] --yes", file=sys.stderr)
            return EXIT_USAGE
    if not profiles:
        print("Nothing selected.")
        return 0

    secrets_file = Path(args.secrets_file).expanduser() if args.secrets_file else None
    try:
        if secrets_file:
            os.environ.update(read_secrets(secrets_file))
        os.environ.update(user_env(load_user(ask if interactive(args) else None)))
        skip = {s.strip() for s in (args.skip or "").split(",") if s.strip()}
        modules = catalog.plan(catalog.profile_modules(profiles), os_name, skip)

        runner = Runner(catalog, os_name)
        print(f"Converging {', '.join(profiles)} ({len(modules)} modules). Logs: {runner.log_dir}")
        results = []
        width = max((len(m.name) for m in modules), default=0)
        for module in modules:
            result = runner.converge(module, dry_run=args.dry_run)
            results.append(result)
            print_table([result], width)
            if result.status == "failed":
                print(f"\nerror: {module.name} did not converge. Log: {result.log}", file=sys.stderr)
                return EXIT_FAILED
    finally:
        if secrets_file and not args.keep_secrets_file and secrets_file.exists():
            secrets_file.unlink()

    changed = [r.module for r in results if r.status in ("installed", "would-install")]
    print(f"\n{len(changed)} changed, {len(results) - len(changed)} already converged.")
    if args.expect_no_changes and changed:
        print(f"error: expected no changes, but {', '.join(changed)} changed", file=sys.stderr)
        return EXIT_CHANGED
    return 0


def cmd_doctor(args) -> int:
    catalog = Catalog.load()
    os_name = current_os()
    runner = Runner(catalog, os_name)
    modules = [m for m in sorted(catalog.modules.values(), key=lambda m: m.name) if os_name in m.os]
    results = [runner.check(m) for m in modules]
    if args.json:
        print(json.dumps([
            {"module": r.module, "status": r.status, "version": r.version, "pin": r.pin, "drift": r.drift}
            for r in results
        ], indent=2))
    else:
        print_table(results)
    return EXIT_FAILED if any(r.drift for r in results) else 0


def cmd_probe(args) -> int:
    found = probe_mod.probe()
    if args.json:
        print(json.dumps(found, indent=2))
    else:
        for key, value in found.items():
            print(f"{key}: {value}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mayhem")
    sub = parser.add_subparsers(dest="command", required=True)

    setup = sub.add_parser("setup", help="converge this machine to one or more profiles")
    setup.add_argument("--profile", help="comma-separated profiles; skips the picker")
    setup.add_argument("--yes", action="store_true", help="no prompts")
    setup.add_argument("--dry-run", action="store_true", help="check only, install nothing")
    setup.add_argument("--skip", help="comma-separated modules to leave alone")
    setup.add_argument("--secrets-file", help="KEY=value file, mode 600; deleted afterwards")
    setup.add_argument("--keep-secrets-file", action="store_true")
    setup.add_argument("--expect-no-changes", action="store_true", help=f"exit {EXIT_CHANGED} if anything changed")
    setup.set_defaults(func=cmd_setup)

    doctor = sub.add_parser("doctor", help="installed versions and drift from versions.toml")
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(func=cmd_doctor)

    probe = sub.add_parser("probe", help="OS, RAM, GPUs and matched tier")
    probe.add_argument("--json", action="store_true")
    probe.set_defaults(func=cmd_probe)

    args = parser.parse_args(argv)
    # Progress lines must interleave with errors on stderr, even through a pipe or CI log.
    sys.stdout.reconfigure(line_buffering=True)
    try:
        return args.func(args)
    except (CatalogError, SecretsError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_FAILED
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
