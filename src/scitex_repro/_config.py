#!/usr/bin/env python3
"""Local config helper replacing scitex.config.get_paths dependency.

Uses SCITEX_DIR env var or defaults to ~/.scitex/.
"""

from __future__ import annotations

import scitex_logging as slogging
import os
import shutil
import warnings
from pathlib import Path

log = slogging.getLogger(__name__)

# Package short name: scitex-repro → repro (prefix-stripping rule, §2 of
# 06_local-state-directories.md).
_PKG_SHORT = "repro"


class _Paths:
    """Minimal path manager for scitex-repro.

    All runtime state lives under ``{base_dir}/repro/runtime/`` per the
    ecosystem local-state-directories convention.
    """

    def __init__(self, base_dir: str | None = None):
        if base_dir is not None:
            self._base_dir = Path(base_dir)
        else:
            self._base_dir = Path(os.environ.get("SCITEX_DIR", Path.home() / ".scitex"))
        self._migrated = False

    # ── Helpers ────────────────────────────────────────────────────────

    def _pkg_root(self) -> Path:
        """Package root directory (tracked + runtime)."""
        return self._base_dir / _PKG_SHORT

    def _runtime_dir(self) -> Path:
        """Regenerable runtime state directory."""
        return self._base_dir / _PKG_SHORT / "runtime"

    def _maybe_migrate(self, new: Path, old: Path) -> None:
        """One-shot migration from legacy ``~/.scitex/rng`` layout."""
        if self._migrated:
            return
        self._migrated = True
        if old.is_dir() and not new.exists():
            new.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old), str(new))
            warnings.warn(
                f"Migrated {old} → {new}. "
                f"The legacy ~/.scitex/rng/ layout is deprecated; "
                f"remove {old} when convenient.",
                DeprecationWarning,
                stacklevel=3,
            )
            log.info("Migrated %s → %s", old, new)

    # ── Public path properties ─────────────────────────────────────────

    @property
    def rng(self) -> Path:
        """Random number generator state directory.

        Resolves to ``{base}/repro/runtime/rng`` per the ecosystem
        local-state-directories convention (§4b).
        """
        new = self._runtime_dir() / "rng"
        old = self._base_dir / "rng"
        self._maybe_migrate(new, old)
        return new


_default_paths: _Paths | None = None


def get_paths(base_dir: str | None = None) -> _Paths:
    """Get path manager instance.

    Parameters
    ----------
    base_dir : str, optional
        Explicit base directory.  If None, returns cached default instance
        using ``SCITEX_DIR`` env-var or ``~/.scitex/``.
    """
    global _default_paths

    if base_dir is not None:
        return _Paths(base_dir)

    if _default_paths is None:
        _default_paths = _Paths()

    return _default_paths
