# Sourced by module scripts. Works under the CLI (which sets MAYHEM_*) and by hand.
set -euo pipefail

MAYHEM_BIN="${MAYHEM_BIN:-$HOME/.local/bin}"

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
as_root() { if [ "$(id -u)" -eq 0 ]; then "$@"; else sudo "$@"; fi; }

# pin NAME: MAYHEM_VERSION when the CLI set it, else NAME's line in the public versions.toml.
pin() {
  if [ -n "${MAYHEM_VERSION:-}" ]; then printf '%s\n' "$MAYHEM_VERSION"; return; fi
  local file value
  file="$(dirname "${BASH_SOURCE[0]}")/../../versions.toml"
  value="$(sed -n "s/^$1[[:space:]]*=[[:space:]]*\"\([^\"]*\)\".*/\1/p" "$file")"
  [ -n "$value" ] || die "no pin for $1 in $file"
  printf '%s\n' "$value"
}

# at_least HAVE FLOOR: true when version HAVE >= FLOOR.
at_least() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]; }

require_amd64() { [ "$(uname -m)" = x86_64 ] || die "only x86_64 is supported (got $(uname -m))"; }

# fetch URL SUMS_URL OUT: download URL to OUT and check it against its line in SUMS_URL
# (sha256sum format, which every release we pin publishes).
fetch() {
  local url=$1 sums=$2 out=$3 name want got
  name="${url##*/}"
  curl -fsSL --retry 3 -o "$out" "$url"
  want="$(curl -fsSL --retry 3 "$sums" | awk -v n="$name" '$2 == n || $2 == "*" n { print $1 }')"
  got="$(sha256sum "$out" | awk '{ print $1 }')"
  [ -n "$want" ] || die "$name is not listed in $sums"
  [ "$want" = "$got" ] || die "checksum mismatch for $name"
}

# install_bin SRC NAME: put an executable into MAYHEM_BIN.
install_bin() { mkdir -p "$MAYHEM_BIN"; install -m 755 "$1" "$MAYHEM_BIN/$2"; }
