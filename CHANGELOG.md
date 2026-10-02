# Changelog

All notable changes to `scitex-repro` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

- fix: resolve RNG state under `repro/runtime/rng` per local-state-directives convention (PR #15)

## [0.1.8] — 2026-10-02

- Replace removed `scitex.logging` calls with the standalone `scitex-logging`
  package and keep verbose diagnostics behind the existing `verbose` flag.
- Require the Logger 0.2.2 and Dev 0.62.2 baselines used by the current genuine
  Python 3.11, 3.12 and 3.13 checks; later releases remain eligible.
- Deliver freshly built documentation as a bounded artifact for content review
  and an ordinary protected PR instead of a rejected direct push to develop.
- Isolate release jobs, verify the CI executable/image, require full extras and
  check source, wheel, sdist and installed runtime files before OIDC publication.

## [0.1.6] — 2026-05-17

- Bump release version for workflow alignment.
- fix(workflows): resync integrated release pipeline from scitex-dev v0.11.20 (#10)
- fix(workflows): resync canonical pypi/rtd-sphinx from scitex-dev (#9)
- fix(workflows): standardize to scitex-dev canonical set (#8)

## [0.1.5] — 2026-04-24

- Bump release version for CI v0.11.20 alignment.
- fix(tests): clear PA-306 + PA-307 test-quality violations (#5)
- ci: normalize workflow filenames + README badges per PS-164
- quality: subprocess-coverage wiring + codecov.yml + workflow merge + audit whitelist
- docs(readme): recommend uv pip install `<pkg>`[all] (faster resolver)
- fix(repro): widen tensorflow / torch import probes past ImportError

## [0.1.4] — 2026-04-23

- audit: clear PS204x2 + PS107/110/112/113 (canonical README + test layout)
- chore(structure): audit-project compliance — tests mirror layout
- fix(release-safety): opt-in publish-pypi.yml (workflow_dispatch only)
- fix(skills): add canonical frontmatter (name, description, tags)
- fix(api): PA501/PA201/PA203 hygiene — `from __future__ import annotations`, `__version__` in `__all__`, fallback `0.0.0+local`

## [0.1.3] — 2026-04-19

- Initial standalone release from monolithic `scitex.repro` module.
- Initial CHANGELOG entry — see git log for prior history.
