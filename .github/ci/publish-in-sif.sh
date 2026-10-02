#!/usr/bin/env bash
# Publish only tag/source/artifact/installed equality-checked OIDC artifacts.
set -euo pipefail
source .github/ci/job-state.sh
V="${1:-3.12}"
source .github/ci/venv-in-sif.sh "$V"
"$PY" .github/ci/check-dist.py --source --dist dist
(cd dist && sha256sum --check SHA256SUMS)
WHEELS=(dist/scitex_repro-*.whl)
[ "${#WHEELS[@]}" -eq 1 ]
"$UV" pip install --python "$PY" "${WHEELS[0]}[all,dev]" twine
"$UV" pip check --python "$PY"
"$PY" -m twine check dist/*.whl dist/*.tar.gz
INSTALLED_SITE="$("$PY" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
"$PY" .github/ci/check-dist.py --dist dist --installed "$INSTALLED_SITE"
"$PY" .github/ci/publish-oidc.py dist
