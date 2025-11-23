# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project overview

This repository contains the source code for **pip**, the Python package installer. The public interface is the `pip`/`pip3` command-line tool; the Python package in `src/pip` exists primarily to implement that CLI.

Authoritative user and contributor documentation lives at:
- User docs: https://pip.pypa.io/en/stable/
- Development docs: https://pip.pypa.io/en/latest/development/

When making non-trivial changes, always cross-check against the development docs and `.github/CONTRIBUTING.md` for project-specific processes (NEWS entries, CI expectations, etc.).

## Development commands

### Nox (preferred entry point)

All routine development workflows are defined in `noxfile.py`. `nox` reuses existing virtualenvs and is the easiest way to run tests, linting, docs builds, and release tasks.

#### Linting and static checks

Runs `pre-commit` (Black, Ruff, mypy, codespell, etc.) across the whole repo:

```bash
nox -s lint
```

You can pass additional arguments after `--` to forward them to `pre-commit`, for example to run a single hook:

```bash
nox -s lint -- ruff-check
```

#### Test suite

The `test` session is parametrized over multiple Python versions (3.9–3.14 and PyPy). Each `test-<version>` session:
- Builds a source distribution using `python -m build`.
- Installs that sdist into the session virtualenv.
- Installs test dependencies from the `test` dependency group defined in `pyproject.toml`.
- Runs `pytest` (by default `-n auto` via `pytest-xdist`).

Run the full test suite for a specific Python version (adjust the version to one you have installed):

```bash
nox -s test-3.11
```

Run a single test module or test selection by passing pytest arguments after `--`:

```bash
nox -s test-3.11 -- tests/unit/test_finder.py -k test_find_links
```

#### Documentation

Build Sphinx docs (HTML + man pages) into `docs/build/`:

```bash
nox -s docs
```

Run an auto-rebuilding docs server using `sphinx-autobuild`:

```bash
nox -s docs-live
```

#### Coverage

Run tests with coverage enabled, writing coverage data into `.coverage-output/` as configured in `pyproject.toml`:

```bash
nox -s coverage -- -n auto
```

Append additional pytest arguments after `--` as needed (e.g., to focus on specific tests).

#### Vendoring third-party libraries

Vendored dependencies live under `src/pip/_vendor` and are managed via the `vendoring` tool configured in `pyproject.toml`.

Synchronize vendored libraries without upgrading versions:

```bash
nox -s vendoring
```

Upgrade specific vendored libraries or all of them (this also writes `news/<lib>.vendor.rst` fragments and commits changes via `tools/release`):

```bash
# Upgrade a specific vendored library
nox -s vendoring -- --upgrade requests

# Upgrade all vendored libraries
nox -s vendoring -- --upgrade-all
```

This session creates Git commits and should be run on a dedicated branch, not directly on `main`.

#### Release workflow

Release automation is implemented in `noxfile.py` using helper functions from `tools/release`:

- Prepare a release (regenerate `AUTHORS.txt`, generate `NEWS.rst` from `news/` fragments, bump `src/pip/__init__.py`, tag the release, and bump to the next dev version):

  ```bash
  nox -s prepare-release -- YY.N[.P]
  ```

- Build release artifacts (wheel + sdist) into `dist/` using `build-project/build-project.py` and validate them with `twine check`:

  ```bash
  nox -s build-release -- YY.N[.P]
  ```

- Upload built artifacts in `dist/` to PyPI using `twine upload`:

  ```bash
  nox -s upload-release -- YY.N[.P]
  ```

Follow the development and release docs for the exact versioning scheme and process; these sessions assume a clean Git state and will error if there are staged or untracked files that could affect a release.

### Direct tool usage

While Nox is preferred, some tools can be run directly:

- Run all configured pre-commit hooks without Nox:

  ```bash
  pre-commit run --all-files
  ```

- Pytest configuration (addopts, markers, ignores) is centralized in `pyproject.toml` under `[tool.pytest.ini_options]`. If you run `pytest` directly, that configuration will be picked up automatically.

## Code architecture

### High-level layout

The project uses `src`-based layout and separates library code, tests, docs, and release tooling:

- `src/pip/` — main package implementing pip.
- `tests/` — unit and functional tests.
- `docs/` — Sphinx documentation sources and configuration.
- `build-project/` — scripts for building release artifacts used by the `build-release` Nox session.
- `tools/` — internal tooling for releases and vendoring.
- `.nox/`, `.venv/` — local virtual environments created by Nox or the developer; do not edit anything under these directories.

### `src/pip` internals

`src/pip` contains the `pip` package and CLI entry points:

- `pip/__main__.py` and `pip/__pip-runner__.py` provide the console entry points used by the `pip`/`pip3` scripts defined in `pyproject.toml`.
- `pip/_internal/` holds the implementation details; its modules are considered internal to pip and are not a supported public API for external projects.

Within `pip._internal`, responsibilities are split by domain:

- `cli/` — command-line interface front-end (argument parsing, main parser, autocompletion, progress bars, status codes) that ultimately dispatches to command implementations.
- `commands/` — implementations of top-level pip commands (`install`, `uninstall`, `list`, `wheel`, `cache`, etc.), each subclassing a base command type.
- `index/` and `locations/` — logic for interacting with package indexes, index URLs, and determining installation locations for different environments and schemes.
- `req/`, `resolution/`, and `models/` — requirement objects, dependency resolution (including the resolvelib-based resolver), and supporting data models (candidates, links, target Python, installation schemes, etc.).
- `network/` — HTTP/session handling, caching, authentication, download utilities, and XML-RPC client code for talking to package indexes.
- `operations/` and `distributions/` — orchestration of install/uninstall/editable operations and helpers for working with sdists and wheels.
- `metadata/` — reading and normalizing package metadata from different backends (importlib, `pkg_resources`, JSON metadata, etc.).
- `utils/` — shared utilities (filesystem helpers, compatibility shims, hashing, temp directories, logging, retry logic, unpacking helpers, etc.).
- `_vendor/` — vendored copies of third-party libraries, synchronized via the `vendoring` tool; do not hand-edit files here.

When implementing or modifying behaviour, prefer to locate the existing module whose responsibility matches the change (for example, new CLI flags for `pip install` usually touch `pip._internal.cli.cmdoptions`, the relevant `pip._internal.commands.*` module, and possibly resolution or operations layers).

### Tests

Tests are organized to mirror the internal structure and to separate unit-level behaviour from end-to-end CLI behaviour:

- `tests/unit/` — fast, isolated tests that primarily exercise individual modules under `pip._internal`. Filenames usually correspond to the module under test (e.g. `tests/unit/test_network_session.py` for `pip._internal.network.session`).
- `tests/functional/` — higher-level tests that drive the `pip` CLI as a black box (installing packages, interacting with indexes, checking resolver behaviour, etc.). These are the right place for tests of new CLI features or end-to-end flows.
- `tests/lib/` — shared test helpers (virtualenv management, local index servers, filesystem utilities, test wheels, etc.) used by both unit and functional tests.

Pytest is configured via `pyproject.toml` to ignore vendored code and certain cache directories, enforce strict `xfail`, and provide markers for networked tests, VCS-specific tests, and unit vs integration tests.

### Configuration and metadata

Most tooling configuration is centralized in `pyproject.toml`:

- Dependency groups `test`, `test-common-wheels`, and `docs` define optional dependencies used by Nox sessions (`pip install --group ...`).
- `[tool.ruff]` defines linting rules and exclusions (notably excluding `_vendor` and build artifacts) and sets the target version to Python 3.9.
- `[tool.mypy]` enables strict type checking for `src/pip`, with relaxed settings or ignored errors for vendored modules and specific internal helpers.
- `[tool.pytest.ini_options]` configures default pytest options, ignores, and markers.
- `[tool.coverage.*]` configures coverage collection paths and output location, used by the `coverage` Nox session.
- `[tool.towncrier]` and related sections describe how NEWS fragments in `news/` are grouped and rendered into `NEWS.rst`.
- `[tool.vendoring]` describes how vendored libraries are pulled into `src/pip/_vendor` from `src/pip/_vendor/vendor.txt` and how licenses are handled.

`.pre-commit-config.yaml` defines the exact hooks that `nox -s lint` runs (pre-commit hooks, Black, Ruff, mypy, RST checks, codespell). If you see formatting or style changes in unrelated files, they likely come from these hooks.
