"""E2E: same seed reproduces the same stream; verify() agrees twice (PS-212).

Drives the real ``RandomStateManager`` + ``hash_array`` against real numpy
state. No network, loopback-only by construction (pure in-memory + tmp).
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e

from scitex_repro import RandomStateManager, hash_array


def test_same_seed_same_stream() -> None:
    # Arrange
    first = RandomStateManager(seed=42)("e2e-a").random(10)
    # Act
    second = RandomStateManager(seed=42)("e2e-a").random(10)
    # Assert
    assert bool((first == second).all()) is True


def test_different_seed_different_stream() -> None:
    # Arrange
    first = RandomStateManager(seed=42)("e2e-b").random(10)
    # Act
    second = RandomStateManager(seed=43)("e2e-b").random(10)
    # Assert
    assert bool((first == second).all()) is False


def test_verify_caches_then_confirms(capsys: pytest.CaptureFixture[str]) -> None:
    # Arrange
    mgr = RandomStateManager(seed=7)
    data = mgr("e2e-c").random(10)
    # Act
    cached = mgr.verify(data, "e2e-verify-cache")
    confirmed = mgr.verify(data, "e2e-verify-cache")
    captured = capsys.readouterr()
    # Assert
    assert (cached, confirmed, captured.out, captured.err) == (
        True,
        True,
        "OK: Reproducibility verified for 'e2e-verify-cache'\n",
        "",
    )


def test_hash_array_stable() -> None:
    # Arrange
    mgr = RandomStateManager(seed=7)
    data = mgr("e2e-d").random(10)
    # Act
    fingerprint = hash_array(data)
    # Assert
    assert fingerprint == hash_array(data)
