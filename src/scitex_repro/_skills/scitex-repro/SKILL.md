---
name: scitex-repro
description: |
  [WHAT] Reproducibility helpers for scientific Python experiments — unified seeded random-state for `random`/`numpy`/`torch`/`tf`, experiment ID + timestamp generation, and deterministic hashing of numpy arrays. Public API (9 symbols) — random state (`RandomStateManager` — class that fixes seeds across `random`, `numpy.random`, `torch`, `tensorflow`, `os.environ[PYTHONHASHSEED]` in one call…
  [WHEN] Use whenever the user asks to "seed this experiment deterministically", "seed numpy and torch together", "generate an experiment ID for this run", "make an output folder name like 20261023_1530_abc12345", "hash a numpy array for reproducibility", "reset the RNG mid-experiment", or mentions `RandomStateManager`, `gen_ID`, `hash_array`, `scitex.
  [HOW] repro`, seed-everything.
tags: [scitex-repro]
primary_interface: python
interfaces:
  python: 3
  cli: 0
  mcp: 0
  skills: 2
  http: 0
---

# scitex-repro

> **Interfaces:** Python ⭐⭐⭐ (primary) · CLI — · MCP — · Skills ⭐⭐ · Hook — · HTTP —

Small utility package that bundles the reproducibility helpers extracted
from the monolithic `scitex.repro` module. Four concerns:

## Installation & import (two equivalent paths)

The same module is reachable via two install paths. Both forms work at
runtime; which one a user has depends on their install choice.

```python
# Standalone — pip install scitex-repro
import scitex_repro
scitex_repro.gen_ID(...)

# Umbrella — pip install scitex
import scitex.repro
scitex.repro.gen_ID(...)
```

`pip install scitex-repro` alone does NOT expose the `scitex` namespace;
`import scitex.repro` raises `ModuleNotFoundError`. To use the
`scitex.repro` form, also `pip install scitex`.

See [../../general/02_interface-python-api.md] for the ecosystem-wide
rule and empirical verification table.

1. Random state — `RandomStateManager`, `get`, `reset`
2. ID / timestamp generation — `gen_ID`, `gen_id`, `gen_timestamp`, `timestamp`
3. Array hashing — `hash_array`
4. Legacy `fix_seeds` shim (deprecated)

## Sub-skills

- [01_installation.md](01_installation.md) — pip install + verify
- [02_quick-start.md](02_quick-start.md) — install, import, one snippet per area
- [03_python-api.md](03_python-api.md) — full public symbol table with signatures

## CLI ownership

The standalone `scitex-repro` distribution has no console command, module-entry
CLI, or MCP tools. Its Python API is the interface for seeding the running
experiment.

The `scitex` umbrella supplies the separate `scitex repro` CLI adapter. Install
`scitex[repro]` to use that route; installing only `scitex-repro` does not install
the `scitex` command. The umbrella owns command registration, options and errors.
For available commands, use `scitex repro --help`.

The owning umbrella source is
[`src/scitex/cli/repro.py`](https://github.com/scitex-ai/scitex-python/blob/develop/src/scitex/cli/repro.py),
registered through `src/scitex/cli/_lazy_subcommands.py`. It provides `gen-id`,
`gen-timestamp`, `hash` and `seed`. A CLI seed applies within that command's
process; use `RandomStateManager` inside the experiment to seed its generators.


## Environment

- [10_env-vars.md](10_env-vars.md) — SCITEX_* env vars read by scitex-repro at runtime
