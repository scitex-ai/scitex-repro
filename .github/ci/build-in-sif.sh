#!/usr/bin/env bash
# Build and compare every runtime file before publishing the checked-out tag.
set -euo pipefail
source .github/ci/job-state.sh
V="${1:-3.12}"
source .github/ci/venv-in-sif.sh "$V"
"$PY" .github/ci/check-dist.py --source
"$UV" pip install --python "$PY" ".[all,dev]" build twine
"$UV" pip check --python "$PY"
rm -rf dist
"$PY" -m build --installer uv --outdir dist
"$PY" -m twine check dist/*.whl dist/*.tar.gz
"$PY" .github/ci/check-dist.py --dist dist
WHEELS=(dist/scitex_repro-*.whl)
[ "${#WHEELS[@]}" -eq 1 ]
"$UV" venv --python "$BASE_PY" "$REPRO_CI_STATE/installed-venv"
INSTALLED_PY="$REPRO_CI_STATE/installed-venv/bin/python"
"$UV" pip install --python "$INSTALLED_PY" "${WHEELS[0]}[all,dev]"
"$UV" pip check --python "$INSTALLED_PY"
INSTALLED_SITE="$("$INSTALLED_PY" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
"$INSTALLED_PY" .github/ci/check-dist.py --dist dist --installed "$INSTALLED_SITE"
(cd dist && sha256sum *.whl *.tar.gz > SHA256SUMS)
