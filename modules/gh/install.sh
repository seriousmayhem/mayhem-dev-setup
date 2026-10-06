#!/usr/bin/env bash
. "${MAYHEM_LIB:-$(dirname "$0")/../_lib}/lib.sh"
require_amd64

v="$(pin gh)"
base="https://github.com/cli/cli/releases/download/v$v"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
fetch "$base/gh_${v}_linux_amd64.tar.gz" "$base/gh_${v}_checksums.txt" "$tmp/gh.tar.gz"
tar -xzf "$tmp/gh.tar.gz" -C "$tmp"
install_bin "$tmp/gh_${v}_linux_amd64/bin/gh" gh
