#!/usr/bin/env bash
. "${MAYHEM_LIB:-$(dirname "$0")/../_lib}/lib.sh"

have="$("$MAYHEM_BIN/gh" --version 2>/dev/null | awk 'NR == 1 { print $3 }')" || true
echo "$have"
[ -n "$have" ] && [ "$have" = "$(pin gh)" ]
