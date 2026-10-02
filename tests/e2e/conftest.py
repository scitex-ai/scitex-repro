"""E2E isolation: verify() writes hash caches under $SCITEX_DIR.

Redirect ``SCITEX_DIR`` to a tmp dir so the real ``~/.scitex`` is never
touched. No monkeypatch (PA-306): explicit save/restore with try/finally.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_scitex_home(tmp_path: Path) -> Iterator[None]:
    previous = os.environ.get("SCITEX_DIR")
    os.environ["SCITEX_DIR"] = str(tmp_path / "scitex-home")
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("SCITEX_DIR", None)
        else:
            os.environ["SCITEX_DIR"] = previous
