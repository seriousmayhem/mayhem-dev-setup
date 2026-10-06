#!/usr/bin/env bash
. "${MAYHEM_LIB:-$(dirname "$0")/../_lib}/lib.sh"

# ~/.bash_profile, when present, stops bash reading ~/.profile, so both carry the line.
for rc in ~/.profile ~/.bash_profile; do
  [ -f "$rc" ] || [ "$rc" = ~/.profile ] || continue
  grep -qF "\"$MAYHEM_BIN:" "$rc" 2>/dev/null || exit 1
done
echo "$MAYHEM_BIN"
