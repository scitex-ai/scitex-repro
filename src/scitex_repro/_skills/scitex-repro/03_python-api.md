---
description: |
  [TOPIC] Python Api
  [DETAILS] scitex-repro — Python API — see file body for details.
tags: [scitex-repro-python-api]
---

<!-- 02_python-api.md -->

# scitex-repro — Python API

Public symbols in `scitex_repro.__all__`:

| Symbol | Kind | One-liner |
|--------|------|-----------|
| `RandomStateManager` | class | Seeded RNG manager with named generators, verify cache, checkpoints. |
| `get` | function | Return (or lazily create) the module-level `RandomStateManager`. |
| `reset` | function | Rebuild the module-level singleton with a new seed. |
| `gen_ID` | function | Unique ID = formatted timestamp + N random alphanumerics. |
| `gen_id` | function | Lowercase alias of `gen_ID`. |
| `gen_timestamp` | function | Short filename-safe timestamp string. |
| `timestamp` | function | Alias of `gen_timestamp`. |
| `hash_array` | function | Deterministic hex hash of a numpy array. |
| `fix_seeds` | function | **Deprecated.** Back-compat wrapper that returns `RandomStateManager(seed)`. |

## Signatures

Reference signatures (not an executable example). `Path` is `pathlib.Path`.

```text
class RandomStateManager:
    def __init__(self, seed: int = 42, verbose: bool = False) -> None: ...
    def __call__(self, name: str, verbose: bool | None = None) -> "numpy.random.Generator": ...
    def get_np_generator(self, name: str) -> "numpy.random.Generator": ...
    def get_sklearn_random_state(self, name: str) -> int: ...
    def get_torch_generator(self, name: str) -> "torch.Generator": ...
    def verify(self, obj: Any, name: str | None = None, verbose: bool = True) -> bool: ...
    def checkpoint(self, name: str = "checkpoint") -> Path: ...
    def restore(self, checkpoint: str | Path) -> None: ...
    def temporary_seed(self, seed: int): ...   # context manager
    def clear_cache(self, patterns: str | list[str] | None = None) -> int: ...

get(verbose: bool = False) -> RandomStateManager
reset(seed: int = 42, verbose: bool = False) -> RandomStateManager

gen_ID(time_format: str = "%YY-%mM-%dD-%Hh%Mm%Ss", N: int = 8) -> str
gen_id(time_format: str = "%YY-%mM-%dD-%Hh%Mm%Ss", N: int = 8) -> str
gen_timestamp() -> str
timestamp() -> str

hash_array(array_data: "numpy.ndarray") -> str

fix_seeds(seed=42, os=True, random=True, np=True, torch=True,
          tf=False, jax=False, verbose=False, **kwargs) -> RandomStateManager  # deprecated
```

## Manager lifecycle and verification

`reset(seed=123)` returns a new module-level singleton; assign its result to use
it. Existing references keep pointing to their previous manager. To restart
local named streams, construct a new manager with the same seed.

`RandomStateManager.verify` caches a hash the first time it sees `name` and
returns `True`. A later match returns `True`. A mismatch raises `ValueError`
with the default `verbose=True`; with `verbose=False` it returns `False`.
The mismatch leaves the original cached hash in place.

`checkpoint()` writes a pickle file and returns its `pathlib.Path`.
`restore()` accepts that path (or its string form), reseeds the manager and
restores the named-generator states saved in that file. Use your own checkpoint
files; restoring loads their pickle content.

```python
import numpy as np
from scitex_repro import RandomStateManager

rng = RandomStateManager(seed=42)
gen = rng("lifecycle_example")
gen.random(10)
checkpoint = rng.checkpoint("lifecycle_example")
expected = gen.random(5)
rng.restore(checkpoint)
np.testing.assert_array_equal(rng("lifecycle_example").random(5), expected)
```

Owning implementation: `_RandomStateManager.py` (`reset`, `verify`, `checkpoint`,
`restore`). Existing behavioral controls:
`tests/scitex_repro/test__RandomStateManager.py`, including
`test_reset_replaces_previous_global_instance_with_new_object`,
`test_restore_reproduces_post_checkpoint_stream_for_named_generator`,
`test_verify_falsey_verbose_mismatch_preserves_cache_and_returns_false`, and
`test_verify_verbose_mismatch_keeps_exception_and_stderr_diagnostics`.
