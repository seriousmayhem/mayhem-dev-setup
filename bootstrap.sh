#!/usr/bin/env bash
# curl -fsSL https://github.com/seriousmayhem/mayhem-dev-setup/releases/latest/download/bootstrap.sh | bash
# curl -fsSL .../bootstrap.sh | bash -s -- --profile worker,inference --yes --secrets-file ~/join.env
#
# Installs git and uv, checks out the latest signed release into ~/.mayhem/setup, installs the
# mayhem CLI from it and runs `mayhem setup ARGS`.
#   MAYHEM_REF=<tag|branch|sha>  converge something other than the latest release tag
#   --allow-unsigned             required when the ref isn't a tag signed by ALLOWED_SIGNERS
set -euo pipefail

REPO_URL="${MAYHEM_REPO_URL:-https://github.com/seriousmayhem/mayhem-dev-setup.git}"
# Must match allowed_signers at the repo root (the release workflow checks).
ALLOWED_SIGNERS='release@mayhem-dev-setup namespaces="git" ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINyqq6OqUQSxwQ4M5zCAjwsa8ToAYXP9Dd2YG+eTcPar'

say() { printf '==> %s\n' "$*" >&2; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }
as_root() { if [ "$(id -u)" -eq 0 ]; then "$@"; else sudo "$@"; fi; }

ensure_git() {
  command -v git >/dev/null && return
  say "Installing git"
  as_root apt-get update -qq
  as_root apt-get install -y -qq git ca-certificates
}

ensure_uv() {
  export PATH="$HOME/.local/bin:$PATH"
  command -v uv >/dev/null && return
  say "Installing uv"
  # uv isn't packaged for Ubuntu 24.04 or 26.04; Astral's installer is the native one.
  curl -LsSf https://astral.sh/uv/install.sh | sh
}

latest_tag() {
  git ls-remote --tags --refs --sort=-v:refname "$REPO_URL" 'v*' | awk -F'refs/tags/' 'NR == 1 { print $2 }'
}

verify_tag() {
  local signers rc=0
  signers="$(mktemp)"
  printf '%s\n' "$ALLOWED_SIGNERS" >"$signers"
  git -C "$1" -c gpg.format=ssh -c gpg.ssh.allowedSignersFile="$signers" \
    verify-tag "refs/tags/$2" >/dev/null || rc=1
  rm -f "$signers"
  return "$rc"
}

resolve() {
  git -C "$1" rev-parse -q --verify "refs/tags/$2^{commit}" ||
    git -C "$1" rev-parse -q --verify "refs/remotes/origin/$2^{commit}" ||
    git -C "$1" rev-parse -q --verify "$2^{commit}"
}

main() {
  local allow_unsigned=0 args=() arg
  for arg in "$@"; do
    if [ "$arg" = --allow-unsigned ]; then allow_unsigned=1; else args+=("$arg"); fi
  done

  ensure_git
  ensure_uv

  local dest="${MAYHEM_HOME:-$HOME/.mayhem}/setup"
  local ref="${MAYHEM_REF:-}"
  if [ -z "$ref" ]; then
    ref="$(latest_tag)"
    [ -n "$ref" ] || die "no v* release tag on $REPO_URL (set MAYHEM_REF and pass --allow-unsigned)"
  fi

  if [ ! -d "$dest/.git" ]; then
    say "Cloning $REPO_URL into $dest"
    mkdir -p "$(dirname "$dest")"
    git clone --quiet --no-checkout "$REPO_URL" "$dest"
  fi
  # No --force on tags: a release tag that moved upstream must fail here, not get adopted.
  git -C "$dest" fetch --quiet --tags origin '+refs/heads/*:refs/remotes/origin/*'

  if verify_tag "$dest" "$ref"; then
    say "Verified signed release $ref"
  elif [ "$allow_unsigned" -eq 1 ]; then
    say "WARNING: converging unsigned ref $ref"
  else
    die "$ref is not a release tag signed by an allowed key (pass --allow-unsigned to override)"
  fi

  local commit
  commit="$(resolve "$dest" "$ref")" || die "unknown ref $ref"
  git -C "$dest" -c advice.detachedHead=false checkout --quiet --force --detach "$commit"

  say "Installing the mayhem CLI"
  uv tool install --quiet --force --editable "$dest"
  local bin
  bin="$(uv tool dir --bin)/mayhem"

  # Under curl | bash, stdin is the script; the setup picker needs the terminal.
  if (: </dev/tty) 2>/dev/null; then
    exec "$bin" setup "${args[@]}" </dev/tty
  fi
  exec "$bin" setup "${args[@]}"
}

# Called last so a truncated download runs nothing.
main "$@"
