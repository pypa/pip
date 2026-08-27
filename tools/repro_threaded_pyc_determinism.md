# Standalone threaded bytecode determinism reproducer

[`repro_threaded_pyc_determinism.py`](repro_threaded_pyc_determinism.py)
isolates byte differences observed when a free-threaded CPython build compiles
identical source files serially and with a thread pool. It uses only the Python
standard library and does not import, execute, or otherwise involve pip.

The script:

- Generates 64 copies of a minimized source fixture by default.
- Runs serial and threaded compilation in fresh child interpreters.
- Uses fixed logical filenames, `PYTHONHASHSEED=0`, and
  `SOURCE_DATE_EPOCH=1704067200`.
- Produces either checked-hash `.pyc` files with `py_compile` or raw
  `marshal.dumps(compile(...))` payloads.
- Compares the bytes and recursively compares documented code-object fields
  after unmarshalling.
- Preserves `result.json` and the first differing serial/threaded pair.

## Reproduction

Use a new or empty output directory for each invocation. The script refuses to
remove a non-empty output directory.

Free-threaded build with the GIL disabled:

```console
python3.14t tools/repro_threaded_pyc_determinism.py --gil off --backend py_compile --workers 4 --output repro-ft-off-pyc --require-difference
```

The same build with its GIL re-enabled:

```console
python3.14t tools/repro_threaded_pyc_determinism.py --gil on --backend py_compile --workers 4 --output repro-ft-on-pyc --require-difference
```

To bypass `.pyc` header generation and `py_compile`, use the raw marshal
backend:

```console
python3.14t tools/repro_threaded_pyc_determinism.py --gil off --backend marshal --workers 4 --output repro-ft-off-marshal --require-difference
python3.14t tools/repro_threaded_pyc_determinism.py --gil on --backend marshal --workers 4 --output repro-ft-on-marshal --require-difference
```

Run a standard-build control without `--require-difference`:

```console
python3.14 tools/repro_threaded_pyc_determinism.py --backend py_compile --workers 4 --output repro-standard-pyc
python3.14 tools/repro_threaded_pyc_determinism.py --backend marshal --workers 4 --output repro-standard-marshal
```

Set `--workers` to the number of processors available to the process. Other
useful options are `--files`, `--attempts`, and `--fixture`. A run with
`--require-difference` exits with status 1 if no difference is found.

## Result format

`result.json` records the Python and platform versions, available CPU count,
free-threaded build marker, requested and observed GIL state, workload, and
each attempt's differing-file count. For a difference it also records hashes,
sizes, changed offsets, header equality, and `semanticDifferences`.

An empty `semanticDifferences` list means the recursive comparison found equal
values for the inspected code-object fields, including bytecode, constants,
names, filenames, line tables, exception tables, and nested code objects. It
does not prove that the object identity or alias graph is identical.

## Observed Windows results

Environment: Windows 11 prerelease VM, eight virtual CPUs, CPython 3.15.0rc1
free-threaded build, and the corresponding standard CPython 3.15 build. Each
case used 64 files and eight workers.

| Build | Requested GIL | Backend | Outcome |
| --- | --- | --- | --- |
| Free-threaded | Off | `py_compile` | Reproduced on attempt 1; 49 differing bytes in a 3,447-byte `.pyc`; identical 16-byte headers |
| Free-threaded | On | `py_compile` | Reproduced on attempt 2; 49 differing bytes in a 3,447-byte `.pyc`; identical 16-byte headers |
| Free-threaded | Off | `marshal` | Reproduced on attempt 2; 49 differing bytes in a 3,431-byte payload |
| Free-threaded | On | `marshal` | Reproduced on attempt 1; 49 differing bytes in a 3,431-byte payload |
| Standard | Default/on | `py_compile` | No difference in 10 attempts |
| Standard | Default/on | `marshal` | No difference in 10 attempts |

The changed raw-marshal offsets were exactly 16 bytes earlier than the
corresponding `.pyc` offsets, confirming that the `.pyc` header was not the
source of the difference. All inspected decoded code-object field values were
equal.

## Observed WSL results

Environment: Ubuntu 26.04 LTS on WSL2, kernel
`6.18.33.2-microsoft-standard-WSL2`, native ext4 storage, and four available
CPUs. Each case used 64 files and four workers.

| Build | Requested GIL | Backend | Outcome |
| --- | --- | --- | --- |
| CPython 3.14.7 free-threaded | Off | `py_compile` | Reproduced on attempt 1 in 2 files; 50 differing bytes per 3,343-byte `.pyc`; identical 16-byte headers |
| CPython 3.14.7 free-threaded | On | `py_compile` | Reproduced on attempt 1 in 2 files; 50 differing bytes per 3,343-byte `.pyc`; identical 16-byte headers |
| CPython 3.14.7 free-threaded | Off | `marshal` | Reproduced on attempt 1 in 2 files; 50 differing bytes per 3,327-byte payload |
| CPython 3.14.7 free-threaded | On | `marshal` | Reproduced on attempt 1 in 2 files; 50 differing bytes per 3,327-byte payload |
| CPython 3.14.4 standard | Default/on | `py_compile` | No difference in 10 attempts |
| CPython 3.14.4 standard | Default/on | `marshal` | No difference in 10 attempts |

All inspected decoded code-object field values were equal in the WSL
differences as well.

## Interpretation

The raw marshal backend reproduces without pip, `py_compile`, or `.pyc`
headers, so the behavior is within concurrent compilation and/or marshal's
representation of the resulting code-object graph. Re-enabling the GIL on a
free-threaded build does not prevent it on either Windows or Linux.

The precise CPython cause and runtime significance are not established.
However, byte-different outputs are sufficient to violate deterministic build,
artifact hashing, caching, and reproducible-CI expectations. Until the cause
is understood, build-time detection with
`sysconfig.get_config_var("Py_GIL_DISABLED")` is safer than checking only the
runtime GIL state before enabling threaded bytecode compilation.
