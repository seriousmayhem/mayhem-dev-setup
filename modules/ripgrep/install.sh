#!/usr/bin/env bash
. "${MAYHEM_LIB:-$(dirname "$0")/../_lib}/lib.sh"
require_amd64

v="$(pin ripgrep)"
name="ripgrep-$v-x86_64-unknown-linux-musl"
url="https://github.com/BurntSushi/ripgrep/releases/download/$v/$name.tar.gz"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
fetch "$url" "$url.sha256" "$tmp/$name.tar.gz"
tar -xzf "$tmp/$name.tar.gz" -C "$tmp"
install_bin "$tmp/$name/rg" rg
