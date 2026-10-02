#!/usr/bin/env python3
# Time-stamp: "2026-05-18"
# File: tests/scitex_repro/test__RandomStateManager.py

"""Tests for RandomStateManager class.

All tests follow the SciTeX no-mocks + AAA + single-assert testing
discipline (see scitex general skills 02_package_12_no-mocks.md and
02_package_13_test-quality.md).
"""

import random
import warnings

import numpy as np
import pytest

from scitex_repro import RandomStateManager, fix_seeds, get, reset

# Optional-dependency probes — module-level so individual tests can be
# `@pytest.mark.skipif`'d without putting `pytest.skip(...)` in the body
# (which would count as an extra assertion under STX-TQ007).
try:
    import torch  # noqa: F401
    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False

try:
    import pandas as _pd  # noqa: F401
    _HAS_PANDAS = True
except ImportError:
    _HAS_PANDAS = False

_TORCH_REQUIRED = pytest.mark.skipif(not _HAS_TORCH, reason="PyTorch not installed")
_PANDAS_REQUIRED = pytest.mark.skipif(not _HAS_PANDAS, reason="pandas not installed")


# ============================================================================
# Basic construction
# ============================================================================

def test_random_state_manager_instance_is_not_none_when_constructed():
    # Arrange
    seed = 42
    # Act
    mgr = RandomStateManager(seed=seed, verbose=False)
    # Assert
    assert mgr is not None


def test_random_state_manager_records_seed_on_construction():
    # Arrange
    seed = 42
    # Act
    mgr = RandomStateManager(seed=seed, verbose=False)
    # Assert
    assert mgr.seed == seed


def test_random_state_manager_records_verbose_true_on_construction():
    # Arrange
    # (no inputs)
    # Act
    mgr = RandomStateManager(seed=42, verbose=True)
    # Assert
    assert mgr.verbose is True


def test_random_state_manager_uses_default_seed_42_when_unspecified():
    # Arrange
    # (no inputs)
    # Act
    mgr = RandomStateManager(verbose=False)
    # Assert
    assert mgr.seed == 42


def test_random_state_manager_accepts_custom_seed_value():
    # Arrange
    seed = 123
    # Act
    mgr = RandomStateManager(seed=seed, verbose=False)
    # Assert
    assert mgr.seed == seed


# ============================================================================
# Seed fixing for Python / NumPy / torch
# ============================================================================

def test_construction_seeds_python_random_for_reproducibility():
    # Arrange
    RandomStateManager(seed=42, verbose=False)
    val1 = random.random()
    RandomStateManager(seed=42, verbose=False)
    # Act
    val2 = random.random()
    # Assert
    assert val1 == val2


def test_construction_seeds_numpy_random_for_reproducibility():
    # Arrange
    RandomStateManager(seed=42, verbose=False)
    arr1 = np.random.rand(5)
    RandomStateManager(seed=42, verbose=False)
    # Act
    arr2 = np.random.rand(5)
    # Assert
    assert np.array_equal(arr1, arr2)


def test_different_seeds_produce_different_python_random_outputs():
    # Arrange
    RandomStateManager(seed=42, verbose=False)
    val1 = random.random()
    RandomStateManager(seed=123, verbose=False)
    # Act
    val2 = random.random()
    # Assert
    assert val1 != val2


@_TORCH_REQUIRED
def test_construction_seeds_torch_random_when_torch_is_available():
    # Arrange
    torch = pytest.importorskip("torch")
    RandomStateManager(seed=42, verbose=False)
    t1 = torch.rand(5)
    RandomStateManager(seed=42, verbose=False)
    # Act
    t2 = torch.rand(5)
    # Assert
    assert torch.allclose(t1, t2)


# ============================================================================
# Named generators
# ============================================================================

def test_named_generator_is_not_none_when_requested_via_call():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    gen = mgr("test")
    # Assert
    assert gen is not None


def test_named_generator_via_call_has_random_method():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    gen = mgr("test")
    # Assert
    assert hasattr(gen, "random")


def test_same_name_under_same_seed_produces_identical_samples():
    # Arrange
    mgr1 = RandomStateManager(seed=42, verbose=False)
    data1 = mgr1("data").random(10)
    mgr2 = RandomStateManager(seed=42, verbose=False)
    # Act
    data2 = mgr2("data").random(10)
    # Assert
    assert np.array_equal(data1, data2)


def test_different_names_under_same_seed_produce_different_samples():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    data1 = mgr("data1").random(10)
    # Act
    data2 = mgr("data2").random(10)
    # Assert
    assert not np.array_equal(data1, data2)


def test_get_np_generator_returns_non_none_object():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    gen = mgr.get_np_generator("test")
    # Assert
    assert gen is not None


def test_get_np_generator_result_has_random_method():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    gen = mgr.get_np_generator("test")
    # Assert
    assert hasattr(gen, "random")


def test_call_and_get_np_generator_return_identical_samples_for_same_name():
    # Arrange
    mgr1 = RandomStateManager(seed=42, verbose=False)
    data1 = mgr1("test").random(5)
    mgr2 = RandomStateManager(seed=42, verbose=False)
    # Act
    data2 = mgr2.get_np_generator("test").random(5)
    # Assert
    assert np.array_equal(data1, data2)


# ============================================================================
# Global singleton
# ============================================================================

def test_get_returns_same_global_instance_across_two_calls():
    # Arrange
    mgr1 = get()
    # Act
    mgr2 = get()
    # Assert
    assert mgr1 is mgr2


def test_reset_creates_new_distinct_global_instance():
    # Arrange
    mgr1 = get()
    # Act
    mgr2 = reset(seed=123, verbose=False)
    # Assert
    assert mgr1 is not mgr2


def test_reset_applies_supplied_seed_to_new_global_instance():
    # Arrange
    # (no inputs)
    # Act
    mgr = reset(seed=123, verbose=False)
    # Assert
    assert mgr.seed == 123


def test_reset_replaces_previous_global_instance_with_new_object():
    # Arrange
    reset(seed=42, verbose=False)
    mgr1 = get()
    # Act
    mgr2 = reset(seed=999, verbose=False)
    # Assert
    assert mgr1 is not mgr2


def test_reset_with_999_records_999_on_returned_manager():
    # Arrange
    reset(seed=42, verbose=False)
    # Act
    mgr = reset(seed=999, verbose=False)
    # Assert
    assert mgr.seed == 999


# ============================================================================
# Verification API surface
# ============================================================================

def test_random_state_manager_has_verify_attribute():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    present = hasattr(mgr, "verify")
    # Assert
    assert present


def test_random_state_manager_verify_attribute_is_callable():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    is_callable = callable(mgr.verify)
    # Assert
    assert is_callable


def test_verify_first_call_returns_true_for_freshly_cached_name(tmp_path):
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    mgr._cache_dir = tmp_path
    data = np.array([1, 2, 3, 4, 5])
    # Act
    result = mgr.verify(data, "test_data")
    # Assert
    assert result is True


# ============================================================================
# Reproducibility workflows
# ============================================================================

def test_named_generator_workflow_reproduces_random_array_under_same_seed():
    # Arrange
    mgr1 = RandomStateManager(seed=42, verbose=False)
    data1 = mgr1("experiment").random(100)
    mgr2 = RandomStateManager(seed=42, verbose=False)
    # Act
    data2 = mgr2("experiment").random(100)
    # Assert
    assert np.array_equal(data1, data2)


def test_two_named_generators_reproduce_first_stream_under_same_seed():
    # Arrange
    mgr1 = RandomStateManager(seed=42, verbose=False)
    data1 = mgr1("data").random(10)
    mgr2 = RandomStateManager(seed=42, verbose=False)
    # Act
    data2 = mgr2("data").random(10)
    # Assert
    assert np.array_equal(data1, data2)


def test_two_named_generators_reproduce_second_stream_under_same_seed():
    # Arrange
    mgr1 = RandomStateManager(seed=42, verbose=False)
    _ = mgr1("data").random(10)
    model1 = mgr1("model").random(10)
    mgr2 = RandomStateManager(seed=42, verbose=False)
    _ = mgr2("data").random(10)
    # Act
    model2 = mgr2("model").random(10)
    # Assert
    assert np.array_equal(model1, model2)


def test_generator_streams_independent_of_creation_order_for_data():
    # Arrange
    mgr1 = RandomStateManager(seed=42, verbose=False)
    data1 = mgr1("data").random(10)
    _ = mgr1("model").random(10)
    mgr2 = RandomStateManager(seed=42, verbose=False)
    _ = mgr2("model").random(10)
    # Act
    data2 = mgr2("data").random(10)
    # Assert
    assert np.array_equal(data1, data2)


def test_generator_streams_independent_of_creation_order_for_model():
    # Arrange
    mgr1 = RandomStateManager(seed=42, verbose=False)
    _ = mgr1("data").random(10)
    model1 = mgr1("model").random(10)
    mgr2 = RandomStateManager(seed=42, verbose=False)
    model2 = mgr2("model").random(10)
    # Act
    _ = mgr2("data").random(10)
    # Assert
    assert np.array_equal(model1, model2)


# ============================================================================
# Edge cases — seeds and names
# ============================================================================

def test_random_state_manager_accepts_seed_zero():
    # Arrange
    # (no inputs)
    # Act
    mgr = RandomStateManager(seed=0, verbose=False)
    # Assert
    assert mgr.seed == 0


def test_random_state_manager_accepts_large_seed_value():
    # Arrange
    large_seed = 2**31 - 1
    # Act
    mgr = RandomStateManager(seed=large_seed, verbose=False)
    # Assert
    assert mgr.seed == large_seed


def test_named_generator_with_special_characters_in_name_is_not_none():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    gen = mgr("data-model_v1")
    # Assert
    assert gen is not None


def test_named_generator_with_digit_characters_in_name_is_not_none():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    gen = mgr("data123")
    # Assert
    assert gen is not None


# ============================================================================
# Integration — scientific experiment workflow
# ============================================================================

def test_experiment_workflow_reproduces_data_array_under_same_seed():
    # Arrange
    mgr1 = RandomStateManager(seed=42, verbose=False)
    data1 = mgr1("data").random((100, 10))
    _ = mgr1("model").normal(size=(10, 5))
    mgr2 = RandomStateManager(seed=42, verbose=False)
    # Act
    data2 = mgr2("data").random((100, 10))
    # Assert
    assert np.array_equal(data1, data2)


def test_experiment_workflow_reproduces_model_weights_under_same_seed():
    # Arrange
    mgr1 = RandomStateManager(seed=42, verbose=False)
    _ = mgr1("data").random((100, 10))
    w1 = mgr1("model").normal(size=(10, 5))
    mgr2 = RandomStateManager(seed=42, verbose=False)
    _ = mgr2("data").random((100, 10))
    # Act
    w2 = mgr2("model").normal(size=(10, 5))
    # Assert
    assert np.array_equal(w1, w2)


def test_multi_seed_runs_produce_distinct_first_pair_of_means():
    # Arrange
    means = []
    for seed in (42, 43, 44):
        mgr = RandomStateManager(seed=seed, verbose=False)
        means.append(mgr("data").random(50).mean())
    # Act
    pair = (means[0], means[1])
    # Assert
    assert pair[0] != pair[1]


def test_multi_seed_runs_produce_distinct_second_pair_of_means():
    # Arrange
    means = []
    for seed in (42, 43, 44):
        mgr = RandomStateManager(seed=seed, verbose=False)
        means.append(mgr("data").random(50).mean())
    # Act
    pair = (means[1], means[2])
    # Assert
    assert pair[0] != pair[1]


# ============================================================================
# Checkpoint / restore
# ============================================================================

def test_checkpoint_writes_file_to_disk(tmp_path):
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    mgr._cache_dir = tmp_path
    mgr("data").random(10)
    # Act
    checkpoint_path = mgr.checkpoint("test_checkpoint")
    # Assert
    assert checkpoint_path.exists()


def test_checkpoint_writes_file_with_expected_pkl_name(tmp_path):
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    mgr._cache_dir = tmp_path
    mgr("data").random(10)
    # Act
    checkpoint_path = mgr.checkpoint("test_checkpoint")
    # Assert
    assert checkpoint_path.name == "test_checkpoint.pkl"


def test_restore_reproduces_post_checkpoint_stream_for_named_generator(tmp_path):
    # Arrange
    mgr1 = RandomStateManager(seed=42, verbose=False)
    mgr1._cache_dir = tmp_path
    gen1 = mgr1("data")
    gen1.random(10)
    gen1.random(5)
    checkpoint_path = mgr1.checkpoint("restore_test")
    after_checkpoint = gen1.random(10)
    mgr2 = RandomStateManager(seed=99, verbose=False)
    mgr2._cache_dir = tmp_path
    mgr2.restore(checkpoint_path)
    # Act
    restored = mgr2("data").random(10)
    # Assert
    assert np.array_equal(after_checkpoint, restored)


def test_checkpoint_preserves_data_generator_state_across_restore(tmp_path):
    # Arrange
    mgr1 = RandomStateManager(seed=42, verbose=False)
    mgr1._cache_dir = tmp_path
    data_gen = mgr1("data")
    model_gen = mgr1("model")
    data_gen.random(5)
    model_gen.random(5)
    checkpoint_path = mgr1.checkpoint()
    data_after = data_gen.random(10)
    _ = model_gen.random(10)
    mgr2 = RandomStateManager(seed=1, verbose=False)
    mgr2._cache_dir = tmp_path
    mgr2.restore(checkpoint_path)
    # Act
    data_restored = mgr2("data").random(10)
    # Assert
    assert np.array_equal(data_after, data_restored)


def test_checkpoint_preserves_model_generator_state_across_restore(tmp_path):
    # Arrange
    mgr1 = RandomStateManager(seed=42, verbose=False)
    mgr1._cache_dir = tmp_path
    data_gen = mgr1("data")
    model_gen = mgr1("model")
    data_gen.random(5)
    model_gen.random(5)
    checkpoint_path = mgr1.checkpoint()
    _ = data_gen.random(10)
    model_after = model_gen.random(10)
    mgr2 = RandomStateManager(seed=1, verbose=False)
    mgr2._cache_dir = tmp_path
    mgr2.restore(checkpoint_path)
    _ = mgr2("data").random(10)
    # Act
    model_restored = mgr2("model").random(10)
    # Assert
    assert np.array_equal(model_after, model_restored)


# ============================================================================
# temporary_seed context manager
# ============================================================================

def test_temporary_seed_inside_block_matches_seed_seeded_random_value():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    with mgr.temporary_seed(999):
        temp_val = random.random()
    random.seed(999)
    expected = random.random()
    # Assert
    assert temp_val == expected


def test_temporary_seed_restores_python_random_state_after_block():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    random.seed(42)
    original_val = random.random()
    random.seed(42)
    # Act
    with mgr.temporary_seed(999):
        _ = random.random()
    after_val = random.random()
    # Assert
    assert original_val == after_val


def test_temporary_seed_restores_numpy_random_state_after_block():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    np.random.seed(42)
    original_val = np.random.rand()
    np.random.seed(42)
    # Act
    with mgr.temporary_seed(999):
        _ = np.random.rand()
    after_val = np.random.rand()
    # Assert
    assert original_val == after_val


def test_temporary_seed_propagates_inner_exception_to_caller():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    ctx = pytest.raises(ValueError)
    # Assert
    with ctx:
        with mgr.temporary_seed(999):
            raise ValueError("Test exception")


# ============================================================================
# sklearn random_state helper
# ============================================================================

def test_get_sklearn_random_state_returns_python_int():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    state = mgr.get_sklearn_random_state("split")
    # Assert
    assert isinstance(state, int)


def test_get_sklearn_random_state_returns_value_within_32_bit_range():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    state = mgr.get_sklearn_random_state("split")
    # Assert
    assert 0 <= state < 2**32


def test_get_sklearn_random_state_is_reproducible_for_same_name_and_seed():
    # Arrange
    mgr1 = RandomStateManager(seed=42, verbose=False)
    mgr2 = RandomStateManager(seed=42, verbose=False)
    state1 = mgr1.get_sklearn_random_state("train_test_split")
    # Act
    state2 = mgr2.get_sklearn_random_state("train_test_split")
    # Assert
    assert state1 == state2


def test_get_sklearn_random_state_differs_across_distinct_names():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    state1 = mgr.get_sklearn_random_state("split1")
    # Act
    state2 = mgr.get_sklearn_random_state("split2")
    # Assert
    assert state1 != state2


def test_get_sklearn_random_state_differs_across_distinct_base_seeds():
    # Arrange
    mgr1 = RandomStateManager(seed=42, verbose=False)
    mgr2 = RandomStateManager(seed=123, verbose=False)
    state1 = mgr1.get_sklearn_random_state("split")
    # Act
    state2 = mgr2.get_sklearn_random_state("split")
    # Assert
    assert state1 != state2


# ============================================================================
# torch generator helper
# ============================================================================

@_TORCH_REQUIRED
def test_get_torch_generator_returns_a_torch_generator_instance():
    # Arrange
    torch = pytest.importorskip("torch")
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    gen = mgr.get_torch_generator("model")
    # Assert
    assert isinstance(gen, torch.Generator)


@_TORCH_REQUIRED
def test_get_torch_generator_is_reproducible_for_same_name_and_seed():
    # Arrange
    torch = pytest.importorskip("torch")
    mgr1 = RandomStateManager(seed=42, verbose=False)
    val1 = torch.randn(10, generator=mgr1.get_torch_generator("model"))
    mgr2 = RandomStateManager(seed=42, verbose=False)
    # Act
    val2 = torch.randn(10, generator=mgr2.get_torch_generator("model"))
    # Assert
    assert torch.allclose(val1, val2)


@_TORCH_REQUIRED
def test_get_torch_generator_differs_across_distinct_names_in_one_manager():
    # Arrange
    torch = pytest.importorskip("torch")
    mgr = RandomStateManager(seed=42, verbose=False)
    val1 = torch.randn(10, generator=mgr.get_torch_generator("model1"))
    # Act
    val2 = torch.randn(10, generator=mgr.get_torch_generator("model2"))
    # Assert
    assert not torch.allclose(val1, val2)


@_TORCH_REQUIRED
def test_get_torch_generator_returns_cached_object_for_repeated_name():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    gen1 = mgr.get_torch_generator("model")
    # Act
    gen2 = mgr.get_torch_generator("model")
    # Assert
    assert gen1 is gen2


# ============================================================================
# clear_cache
# ============================================================================

def test_clear_cache_with_no_pattern_removes_all_json_files(tmp_path):
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    mgr._cache_dir = tmp_path
    for name in ("test1.json", "test2.json", "test3.json"):
        (tmp_path / name).write_text("{}")
    # Act
    removed = mgr.clear_cache()
    # Assert
    assert removed == 3


def test_clear_cache_with_no_pattern_leaves_no_json_files(tmp_path):
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    mgr._cache_dir = tmp_path
    for name in ("test1.json", "test2.json", "test3.json"):
        (tmp_path / name).write_text("{}")
    # Act
    mgr.clear_cache()
    remaining = list(tmp_path.glob("*.json"))
    # Assert
    assert remaining == []


def test_clear_cache_with_glob_pattern_removes_matching_files(tmp_path):
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    mgr._cache_dir = tmp_path
    (tmp_path / "exp_001.json").write_text("{}")
    (tmp_path / "exp_002.json").write_text("{}")
    (tmp_path / "other.json").write_text("{}")
    # Act
    removed = mgr.clear_cache("exp_*")
    # Assert
    assert removed == 2


def test_clear_cache_with_glob_pattern_preserves_non_matching_files(tmp_path):
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    mgr._cache_dir = tmp_path
    (tmp_path / "exp_001.json").write_text("{}")
    (tmp_path / "exp_002.json").write_text("{}")
    (tmp_path / "other.json").write_text("{}")
    # Act
    mgr.clear_cache("exp_*")
    # Assert
    assert (tmp_path / "other.json").exists()


def test_clear_cache_with_exact_name_removes_exactly_one_file(tmp_path):
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    mgr._cache_dir = tmp_path
    (tmp_path / "target.json").write_text("{}")
    (tmp_path / "keep.json").write_text("{}")
    # Act
    removed = mgr.clear_cache("target")
    # Assert
    assert removed == 1


def test_clear_cache_with_exact_name_removes_only_target_file(tmp_path):
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    mgr._cache_dir = tmp_path
    (tmp_path / "target.json").write_text("{}")
    (tmp_path / "keep.json").write_text("{}")
    # Act
    mgr.clear_cache("target")
    # Assert
    assert not (tmp_path / "target.json").exists()


def test_clear_cache_with_exact_name_preserves_unrelated_file(tmp_path):
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    mgr._cache_dir = tmp_path
    (tmp_path / "target.json").write_text("{}")
    (tmp_path / "keep.json").write_text("{}")
    # Act
    mgr.clear_cache("target")
    # Assert
    assert (tmp_path / "keep.json").exists()


def test_clear_cache_with_name_list_removes_count_matching_list_length(tmp_path):
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    mgr._cache_dir = tmp_path
    (tmp_path / "a.json").write_text("{}")
    (tmp_path / "b.json").write_text("{}")
    (tmp_path / "c.json").write_text("{}")
    # Act
    removed = mgr.clear_cache(["a", "b"])
    # Assert
    assert removed == 2


def test_clear_cache_with_name_list_preserves_files_not_in_list(tmp_path):
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    mgr._cache_dir = tmp_path
    (tmp_path / "a.json").write_text("{}")
    (tmp_path / "b.json").write_text("{}")
    (tmp_path / "c.json").write_text("{}")
    # Act
    mgr.clear_cache(["a", "b"])
    # Assert
    assert (tmp_path / "c.json").exists()


def test_clear_cache_with_nonexistent_name_returns_zero(tmp_path):
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    mgr._cache_dir = tmp_path
    # Act
    removed = mgr.clear_cache("nonexistent")
    # Assert
    assert removed == 0


def test_clear_cache_with_empty_directory_returns_zero(tmp_path):
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    mgr._cache_dir = tmp_path
    # Act
    removed = mgr.clear_cache()
    # Assert
    assert removed == 0


# ============================================================================
# _compute_hash
# ============================================================================

def test_compute_hash_of_numpy_array_returns_string():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    arr = np.array([1, 2, 3, 4, 5])
    # Act
    h = mgr._compute_hash(arr)
    # Assert
    assert isinstance(h, str)


def test_compute_hash_of_numpy_array_returns_32_char_string():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    arr = np.array([1, 2, 3, 4, 5])
    # Act
    h = mgr._compute_hash(arr)
    # Assert
    assert len(h) == 32


def test_compute_hash_of_list_returns_string():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    h = mgr._compute_hash([1, 2, 3, 4, 5])
    # Assert
    assert isinstance(h, str)


def test_compute_hash_of_list_returns_32_char_string():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    h = mgr._compute_hash([1, 2, 3, 4, 5])
    # Assert
    assert len(h) == 32


def test_compute_hash_of_dict_returns_string():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    h = mgr._compute_hash({"a": 1, "b": 2, "c": 3})
    # Assert
    assert isinstance(h, str)


def test_compute_hash_of_dict_returns_32_char_string():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    h = mgr._compute_hash({"a": 1, "b": 2, "c": 3})
    # Assert
    assert len(h) == 32


def test_compute_hash_of_dict_is_independent_of_key_order():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    h1 = mgr._compute_hash({"a": 1, "b": 2})
    # Act
    h2 = mgr._compute_hash({"b": 2, "a": 1})
    # Assert
    assert h1 == h2


def test_compute_hash_of_tuple_returns_32_char_string():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    h = mgr._compute_hash((1, 2, 3, 4, 5))
    # Assert
    assert len(h) == 32


def test_compute_hash_of_string_returns_32_char_string():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    h = mgr._compute_hash("test string")
    # Assert
    assert len(h) == 32


def test_compute_hash_of_int_returns_32_char_string():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    h = mgr._compute_hash(42)
    # Assert
    assert len(h) == 32


def test_compute_hash_of_float_returns_32_char_string():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    h = mgr._compute_hash(3.14)
    # Assert
    assert len(h) == 32


def test_compute_hash_of_bool_returns_32_char_string():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    h = mgr._compute_hash(True)
    # Assert
    assert len(h) == 32


@_TORCH_REQUIRED
def test_compute_hash_of_torch_tensor_returns_32_char_string():
    # Arrange
    torch = pytest.importorskip("torch")
    mgr = RandomStateManager(seed=42, verbose=False)
    tensor = torch.tensor([1.0, 2.0, 3.0])
    # Act
    h = mgr._compute_hash(tensor)
    # Assert
    assert len(h) == 32


@_PANDAS_REQUIRED
def test_compute_hash_of_pandas_dataframe_returns_32_char_string():
    # Arrange
    import pandas as pd
    mgr = RandomStateManager(seed=42, verbose=False)
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    # Act
    h = mgr._compute_hash(df)
    # Assert
    assert len(h) == 32


@_PANDAS_REQUIRED
def test_compute_hash_of_pandas_series_returns_32_char_string():
    # Arrange
    import pandas as pd
    mgr = RandomStateManager(seed=42, verbose=False)
    series = pd.Series([1, 2, 3, 4, 5])
    # Act
    h = mgr._compute_hash(series)
    # Assert
    assert len(h) == 32


def test_compute_hash_is_deterministic_for_identical_input():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    arr = np.array([1, 2, 3])
    h1 = mgr._compute_hash(arr)
    # Act
    h2 = mgr._compute_hash(arr)
    # Assert
    assert h1 == h2


def test_compute_hash_differs_for_arrays_differing_by_one_element():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    h1 = mgr._compute_hash(np.array([1, 2, 3]))
    # Act
    h2 = mgr._compute_hash(np.array([1, 2, 4]))
    # Assert
    assert h1 != h2


# ============================================================================
# Legacy fix_seeds shim
# ============================================================================

def test_fix_seeds_legacy_helper_is_callable_at_module_level():
    # Arrange
    # (no inputs)
    # Act
    is_callable = callable(fix_seeds)
    # Assert
    assert is_callable


def test_fix_seeds_returns_random_state_manager_instance():
    # Arrange
    # (no inputs)
    # Act
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        mgr = fix_seeds(seed=42)
    # Assert
    assert isinstance(mgr, RandomStateManager)


def test_fix_seeds_returned_manager_records_supplied_seed():
    # Arrange
    # (no inputs)
    # Act
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        mgr = fix_seeds(seed=42)
    # Assert
    assert mgr.seed == 42


def test_fix_seeds_emits_deprecation_warning_when_called():
    # Arrange
    # (no inputs)
    # Act
    ctx = pytest.warns(DeprecationWarning)
    # Assert
    with ctx:
        fix_seeds(seed=42)


def test_fix_seeds_seeds_python_random_module_for_reproducibility():
    # Arrange
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        fix_seeds(seed=42)
    val1 = random.random()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        fix_seeds(seed=42)
    # Act
    val2 = random.random()
    # Assert
    assert val1 == val2


# ============================================================================
# get_generator alias
# ============================================================================

def test_get_generator_alias_returns_object_with_random_method():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    gen = mgr.get_generator("test")
    # Assert
    assert hasattr(gen, "random")


def test_get_generator_alias_returns_object_with_normal_method():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    # Act
    gen = mgr.get_generator("test")
    # Assert
    assert hasattr(gen, "normal")


def test_get_generator_alias_returns_same_object_as_get_np_generator():
    # Arrange
    mgr = RandomStateManager(seed=42, verbose=False)
    gen1 = mgr.get_generator("test")
    # Act
    gen2 = mgr.get_np_generator("test")
    # Assert
    assert gen1 is gen2


# ============================================================================
# Optional-framework seeding — TensorFlow / JAX
# ============================================================================


def test_construction_seeds_tensorflow_random_when_tensorflow_is_available():
    # Arrange
    tf = pytest.importorskip("tensorflow")
    RandomStateManager(seed=42, verbose=False)
    t1 = tf.random.uniform([5])
    RandomStateManager(seed=42, verbose=False)
    # Act
    t2 = tf.random.uniform([5])
    # Assert
    assert bool(tf.reduce_all(tf.equal(t1, t2)))


def test_construction_derives_jax_key_from_seed_when_jax_is_available():
    # Arrange
    jax = pytest.importorskip("jax")
    expected = jax.random.PRNGKey(42)
    # Act
    mgr = RandomStateManager(seed=42, verbose=False)
    # Assert
    assert bool((jax.numpy.asarray(mgr._jax_key) == jax.numpy.asarray(expected)).all())


if __name__ == "__main__":
    import os
    pytest.main([os.path.abspath(__file__)])
