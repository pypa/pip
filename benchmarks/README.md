# pip benchmarks

Offline performance workloads for pip's `pip._internal` APIs and vendored
packaging/resolvelib libraries.

## Run

Use the repository's nox workflow from the repository root. Follow the
[development environment setup](../docs/html/development/getting-started.rst)
to install nox. The benchmark session creates its environment and installs pip
and the benchmark dependency group using the same protected installer as the
test sessions.

Run each workload once, including its result assertions, on Python 3.12:

```console
nox -s benchmark-3.12 -- --benchmark-disable
```

Collect timings:

```console
nox -s benchmark-3.12
```

Select a family or individual graph:

```console
nox -s benchmark-3.12 -- benchmarks/bench_index.py
nox -s benchmark-3.12 -- benchmarks/bench_resolution.py -k transitive
```

Save results, then compare another revision against the most recent saved run:

```console
nox -s benchmark-3.12 -- --benchmark-save=before
nox -s benchmark-3.12 -- --benchmark-compare
```

Saved runs live under `benchmarks/.benchmarks/`, which Git ignores.

The benchmark sessions support the same interpreters as the test sessions.
Arguments after `--` are forwarded to pytest. Nox reuses the environment;
after the first run, `nox -R -s benchmark-3.12` also skips installation.
Benchmarks run sequentially, with no automatic pytest-xdist parallelization.

The configuration places this checkout's `src/` first on the import path. The
`bench_*.py` filenames and separate pytest configuration keep benchmarks out of
ordinary test discovery. The suite does not load `tests/conftest.py` or need the
functional test wheel cache. Sockets are blocked by pytest-subket.

## Coverage

| File | Workloads |
| --- | --- |
| `bench_packaging.py` | 300 requirements, 400 names and versions, sorting, specifiers, markers |
| `bench_corpora.py` | Frozen PyPI metadata and Simple API; nine uv compiled requirement sets |
| `bench_index.py` | HTML/JSON parsing, 32-page fanout, metadata links, wheel tags, candidate ranking, four platform target matrices |
| `bench_install.py` | Wheel metadata, validation, hashing, extraction and installation; 300 and 10,000 files, with/without bytecode |
| `bench_resolution.py` | Single/pinned/application graphs, backtracking, wide graph, 88-root stress, 64-version wrong-package and 256-version transitive conflicts, unsatisfiable graphs, seven NAB smoke scenarios |

The PyPI snapshot was captured on 2026-07-31. The uv corpus retains its
[provenance and license references](corpus/uv_workloads/README.md).
Parsing these corpora does not resolve or download their dependencies.

## Measurement boundaries

- Workload generation, corpus loading, and result assertions happen outside
  timing. Index parsing disables pip's parsed-page cache.
- Resolver timing covers `Resolver.resolve()`, including candidate discovery,
  wheel metadata preparation and dependency resolution. Each sample gets a new
  finder, preparer, session, build tracker, resolver, and requirement objects.
  Requirement-parser cache entries are cleared during setup. Resolver setup and
  temporary-directory cleanup are excluded. Only the generated local wheels are
  candidates, and installed packages are ignored.
- Archive and resolver workloads use three rounds with one invocation per round.
  Setup/teardown runs between rounds. Installations write to a fresh temporary
  scheme, and their resulting RECORD entries are verified outside timing.
  `--benchmark-disable` runs these workloads once and still cleans up.
- User pip configuration and environment variables are isolated. No public index,
  user cache, build dependency download, or installed-environment mutation is
  part of these benchmarks. Generated wheels advertise the extras used by their
  dependency markers so upstream pip evaluates those scenarios correctly.
- Interpreter imports, platform-tag caches, and OS filesystem caches may be warm.
  These are in-process measurements, not process startup or OS cold-cache tests.
  Use the same Python version and machine for revision comparisons; avoid
  running benchmark workers concurrently or with coverage instrumentation.

## Scope

The suite measures packaging operations, index processing, wheel installation,
and offline dependency resolution. Live-network requests, source builds, process
startup, and the internal algorithms of other resolvers are outside its scope.
The NAB-shaped graphs run through pip's own resolver.
