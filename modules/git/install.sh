#!/usr/bin/env bash
. "${MAYHEM_LIB:-$(dirname "$0")/../_lib}/lib.sh"

have="$(git --version 2>/dev/null | awk '{ print $3 }')" || true
if [ -z "$have" ] || ! at_least "$have" "$(pin git)"; then
  as_root apt-get update -qq
  as_root apt-get install -y -qq git
fi

git config --global core.longpaths true
git config --global core.autocrlf false
# Fill in identity only where it's missing; never overwrite what the person set.
[ -z "${MAYHEM_USER_NAME:-}" ] || [ -n "$(git config --global user.name)" ] ||
  git config --global user.name "$MAYHEM_USER_NAME"
[ -z "${MAYHEM_USER_EMAIL:-}" ] || [ -n "$(git config --global user.email)" ] ||
  git config --global user.email "$MAYHEM_USER_EMAIL"
