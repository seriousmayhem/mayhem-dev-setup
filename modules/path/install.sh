#!/usr/bin/env bash
. "${MAYHEM_LIB:-$(dirname "$0")/../_lib}/lib.sh"

line="case \":\$PATH:\" in *\":$MAYHEM_BIN:\"*) ;; *) export PATH=\"$MAYHEM_BIN:\$PATH\" ;; esac  # mayhem"
for rc in ~/.profile ~/.bash_profile; do
  [ -f "$rc" ] || [ "$rc" = ~/.profile ] || continue
  grep -qF "\"$MAYHEM_BIN:" "$rc" 2>/dev/null || printf '\n%s\n' "$line" >>"$rc"
done
