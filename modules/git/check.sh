#!/usr/bin/env bash
. "${MAYHEM_LIB:-$(dirname "$0")/../_lib}/lib.sh"

have="$(git --version 2>/dev/null | awk '{ print $3 }')" || true
echo "$have"
[ -n "$have" ] && at_least "$have" "$(pin git)" || exit 1
[ "$(git config --global core.longpaths)" = true ] || exit 1
[ "$(git config --global core.autocrlf)" = false ] || exit 1
[ -z "${MAYHEM_USER_NAME:-}" ] || [ -n "$(git config --global user.name)" ] || exit 1
[ -z "${MAYHEM_USER_EMAIL:-}" ] || [ -n "$(git config --global user.email)" ] || exit 1
