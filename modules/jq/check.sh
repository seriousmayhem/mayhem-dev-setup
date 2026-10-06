#!/usr/bin/env bash
. "${MAYHEM_LIB:-$(dirname "$0")/../_lib}/lib.sh"

have="$("$MAYHEM_BIN/jq" --version 2>/dev/null)" || true
have="${have#jq-}"
echo "$have"
[ -n "$have" ] && [ "$have" = "$(pin jq)" ]
