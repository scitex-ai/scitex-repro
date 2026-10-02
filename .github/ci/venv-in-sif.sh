#!/usr/bin/env bash
# The approved image provides UV; create a complete job-owned interpreter environment.
V="${1:?python version required}"
case "$V" in 3.11|3.12|3.13) ;; *) echo '::error::unsupported Python version'; exit 1;; esac
BASE_PY="/opt/venv-$V/bin/python"
test -x "$BASE_PY"
UV="$(command -v uv)"
test -x "$UV"
"$UV" venv --python "$BASE_PY" "$REPRO_CI_STATE/venv"
PY="$REPRO_CI_STATE/venv/bin/python"
export PATH="$REPRO_CI_STATE/venv/bin:/usr/local/bin:/usr/bin:/bin"
