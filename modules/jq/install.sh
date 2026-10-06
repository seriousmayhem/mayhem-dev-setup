#!/usr/bin/env bash
. "${MAYHEM_LIB:-$(dirname "$0")/../_lib}/lib.sh"
require_amd64

base="https://github.com/jqlang/jq/releases/download/jq-$(pin jq)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
fetch "$base/jq-linux-amd64" "$base/sha256sum.txt" "$tmp/jq-linux-amd64"
install_bin "$tmp/jq-linux-amd64" jq
