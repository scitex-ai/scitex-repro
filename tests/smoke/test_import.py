"""Smoke: installed package imports and mints an ID (PS-211).

Subprocess-driven (``sys.executable -c ...``) so this proves the installed
distribution resolves — an in-process import would not. Hermetic: no
network, no credentials; ``SCITEX_DIR`` points at a tmp dir via the
subprocess environment.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke


def test_import_and_gen_id_subprocess(tmp_path: Path) -> None:
    # Arrange
    env = dict(os.environ, SCITEX_DIR=str(tmp_path / "scitex-home"))
    argv = [
        sys.executable,
        "-c",
        "from scitex_repro import gen_ID; print(len(gen_ID()) > 0)",
    ]
    # Act
    completed = subprocess.run(
        argv, capture_output=True, text=True, timeout=30, env=env
    )
    # Assert
    assert (completed.returncode, completed.stdout.strip()) == (0, "True")
