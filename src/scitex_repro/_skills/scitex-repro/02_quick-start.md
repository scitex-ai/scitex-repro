---
description: |
  [TOPIC] Quick Start
  [DETAILS] scitex-repro — Quick Start — see file body for details.
tags: [scitex-repro-quick-start]
---

<!-- 01_quick-start.md -->

# scitex-repro — Quick Start

## Install

```bash
pip install scitex-repro
```

## Import

```python
import scitex_repro
```

## Random state management

```python
from scitex_repro import RandomStateManager

rng = RandomStateManager(seed=42)       # auto-fixes os/random/numpy/torch seeds
gen = rng("data")                       # named numpy Generator
x = gen.random(100)
rng.verify(x, "my_data")                # cache + check deterministic hash
```

Or use the module-level singleton:

```python
from scitex_repro import get, reset
rng = get()            # lazy singleton, seed=42
rng = reset(seed=123)  # replace singleton and use the returned manager
```

Existing references still point to the previous manager. `reset` is a module-level
function; manager instances have no `reset()` method. To restart a local named
stream, create a new `RandomStateManager` with the same seed.

## Unique IDs and timestamps

```python
from scitex_repro import gen_ID, gen_timestamp

exp_id = gen_ID(N=8)            # e.g. "2026Y-04M-23D-14h05m12s_Ab3dE7Gh"
ts     = gen_timestamp()         # e.g. "2026-0423-1405"
```

`gen_id` and `timestamp` are lowercase aliases of the same functions.

## Hash a numpy array

```python
import numpy as np
from scitex_repro import hash_array

h = hash_array(np.arange(10))    # stable SHA-based hex digest
```

## Deprecated

```python
from scitex_repro import fix_seeds

fix_seeds(seed=42)  # DeprecationWarning — use RandomStateManager instead
```
