#!/usr/bin/env bash
# Verify the selected executable/image; bind only the public checkout and job state.
set -euo pipefail
INNER="${1:?inner script required}"
shift
case "$INNER" in build-in-sif.sh|publish-in-sif.sh|run-in-sif.sh) ;; *) echo '::error::unknown inner script'; exit 1;; esac
APPTAINER="${SCITEX_CI_APPTAINER:?verified absolute Apptainer path required}"
SIF="${SCITEX_CI_SIF:?verified absolute SIF path required}"
[[ "$APPTAINER" = /* && "$SIF" = /* ]] || { echo '::error::absolute executable/image paths required'; exit 1; }
[ -x "$APPTAINER" ] && [ -f "$SIF" ]
printf '%s  %s\n' 7bdb501fdddbb7264b4e4d6038e0ec27201f63e217519e5f7f0db950c9285ddd "$APPTAINER" | sha256sum --check --status
printf '%s  %s\n' aa5836a6c317640d7e20f01eb79aa7385b3dca2f369b595065c50ba3dd34a7d5 "$SIF" | sha256sum --check --status
: "${RUNNER_TEMP:?job-owned runner temporary directory required}"
STATE="$(mktemp -d "$RUNNER_TEMP/repro-${GITHUB_JOB:?}-${GITHUB_RUN_ID:?}-${GITHUB_RUN_ATTEMPT:?}.XXXXXX")"
mkdir -p "$STATE/apptainer-config" "$STATE/apptainer-tmp"
# Only the publish entry point receives ephemeral OIDC values, via execve's env.
exec /usr/bin/python3 -I -S - "$APPTAINER" "$SIF" "$STATE" "$INNER" "$@" <<'PY_EXEC'
import os
from pathlib import Path
import sys
apptainer, image, state, inner, *arguments = sys.argv[1:]
checkout = str(Path.cwd())
native_home = os.environ["HOME"]
environment = {
    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "HOME": native_home,
    "APPTAINER_CONFIGDIR": state + "/apptainer-config",
    "APPTAINER_TMPDIR": state + "/apptainer-tmp",
    "APPTAINERENV_HOME": native_home,
    "APPTAINERENV_REPRO_CI_STATE": state,
    "APPTAINERENV_GITHUB_REF": os.environ["GITHUB_REF"],
}
if inner == "publish-in-sif.sh":
    for name in ("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "ACTIONS_ID_TOKEN_REQUEST_URL"):
        if not os.environ.get(name):
            raise SystemExit("Publish job requires its ephemeral OIDC context")
        environment["APPTAINERENV_" + name] = os.environ[name]
command = [apptainer, "exec", "--cleanenv", "--no-home", "--containall",
           "--pwd", checkout, "--bind", checkout + ":" + checkout,
           "--bind", state + ":" + state, image, "bash", ".github/ci/" + inner, *arguments]
os.execve(apptainer, command, environment)
PY_EXEC
