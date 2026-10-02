#!/usr/bin/env bash
# Full genuine extras and original assertions in the verified, isolated job.
set -euo pipefail
source .github/ci/job-state.sh
V="${1:?python version required}"
case "$V" in 3.11|3.12|3.13) ;; *) exit 1;; esac
source .github/ci/venv-in-sif.sh "$V"
export MPLBACKEND=Agg MPLCONFIGDIR="$REPRO_CI_STATE/mpl"
export OMP_NUM_THREADS=2 TF_NUM_INTRAOP_THREADS=2 TF_NUM_INTEROP_THREADS=2
mkdir -p "$MPLCONFIGDIR"
"$UV" pip install --python "$PY" ".[all,dev]" 'pytest-xdist>=3.0.0'
"$UV" pip check --python "$PY"
# Four workers bound this small suite independently of a host's 128-core count.
umask 022
ulimit -c 0
exec nice -n 19 ionice -c 3 "$PY" -m pytest tests/ -n 4 --dist load -q \
    --cov=scitex_repro --cov-report="xml:$REPRO_CI_STATE/coverage.xml" \
    --cov-report=term --junitxml="$REPRO_CI_STATE/junit.xml" -p no:cacheprovider
