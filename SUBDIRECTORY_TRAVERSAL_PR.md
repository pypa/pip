# Validate the `subdirectory` URL fragment to prevent path traversal (CWE-22)

## Summary

A requirement URL may carry a `#subdirectory=<path>` fragment that names the
directory *inside* an unpacked source archive that pip should build from:

```
pip install "pkg @ https://example.com/pkg.tar.gz#subdirectory=src/pkg"
```

The fragment was extracted by a bare regex with **no validation** and then
joined directly onto the directory the archive was unpacked into:

```python
# src/pip/_internal/req/req_install.py (before)
return os.path.join(self.source_dir, self.link.subdirectory_fragment or "")
```

That joined path becomes the **working directory handed to the PEP 517 build
backend** and the location pip reads `pyproject.toml` / `setup.py` from. A
fragment such as `#subdirectory=../../../some/path` escapes the unpacked
archive, so pip can be made to **execute a build from an attacker-chosen
directory outside the extracted source tree** — arbitrary code execution at
install/build time, not merely a crash.

This is a path-traversal weakness — **CWE-22 (Improper Limitation of a Pathname
to a Restricted Directory)** — promoted to code execution because the traversed
path is used as a build root.

## Trust boundary

pip treats the contents of an unpacked source archive as the unit it builds.
The directory pip extracts into (`InstallRequirement.source_dir`) is the trust
boundary: everything the build backend touches is supposed to live underneath
it. The `subdirectory` fragment is **attacker-influenced data** — it travels
with the requirement string / index response, both of which originate outside
pip's control:

- a direct `name @ URL` requirement (CLI, `requirements.txt`, or a transitive
  dependency's metadata), and
- a server-controlled **JSON simple-index** response, via `Link.from_json`
  (PEP 691). A malicious or compromised index/mirror can attach the fragment
  to any file URL it serves.

Letting that value steer a path **across** the `source_dir` boundary — and then
using the result as the build CWD — violates the boundary. The fix re-asserts
the invariant "the build root is always inside the unpacked source tree."

## Threat model

| | |
|---|---|
| **Attacker** | Anyone who can influence a requirement URL: a malicious package author, a compromised/typo-squatted index or mirror, or a man-in-the-middle on a non-HTTPS index. |
| **Vector** | The `#subdirectory=` fragment of a `file:`/`http(s):`/VCS requirement URL, delivered via the CLI, a requirements/constraints file, a dependency's `Requires-Dist`, or a JSON simple-index entry. |
| **Precondition** | A buildable project (`pyproject.toml` / `setup.py`) exists at the escape target. This is realistic on multi-user or CI hosts (world-writable `/tmp`, shared caches), or when a prior benign-looking step has already written attacker content to a known location, or by climbing to filesystem root and descending into any predictable path. |
| **Impact** | The PEP 517 backend runs with the escaped directory as its CWD, executing that project's build code → **arbitrary code execution outside the archive trust boundary** during `pip install` / `pip wheel` / `pip download --build`. |
| **Without the bug** | The build root is confined to the unpacked archive; an attacker can only ship code *inside* their own archive (already an accepted, sandboxed-by-extraction trust model). |

## Proof of exploitability (before → after)

A PoC drove pip's real build path — `InstallRequirement.load_pyproject_toml()`
followed by `prepare_metadata()` (which invokes the PEP 517 backend whose CWD is
`unpacked_source_directory`). The `setup.py` planted at the escape target writes
a marker file the instant it is imported.

```
########  UNPATCHED  ########
build backend CWD : .../pip_poc/extracted/../outside
escaped archive?  : True
[!] EXPLOITED: build backend executed from OUTSIDE the archive.
[!] marker written: .../pip_poc/PWNED.txt          # code ran outside the tree

########   PATCHED   ########
[+] BLOCKED at Link construction: InvalidSubdirectoryFragment
                                                   # no marker, no build
```

This behaviour is captured permanently by
`tests/functional/test_install_reqs.py::test_subdirectory_traversal_cannot_escape_build_dir`,
which asserts the marker is **never** written.

## The fix (defense in depth, two layers)

1. **Validate at the source** — `Link._subdirectory_fragment()` rejects any
   fragment that is absolute, carries a Windows drive letter, contains control
   characters, or uses `..` to climb out of its starting directory. Both the
   **literal and the percent-decoded** forms are checked under **POSIX and
   Windows** path semantics, so `..%2F..`, `..\..`, `C:\…`, `\\host\share`,
   `/etc/passwd`, and NUL/control-char injection are all caught. The fragment
   is computed once in `Link.__init__`, mirroring the existing `egg` fragment
   validation, so **no consumer can ever observe an unsafe value**. Rejection
   raises a new `InvalidSubdirectoryFragment` diagnostic.

2. **Containment check at the sink** — `InstallRequirement
   .unpacked_source_directory` independently verifies (via `is_within_directory`)
   that the joined path stays inside `source_dir` before it is handed to the
   build backend, so even a future bypass of layer 1 cannot reach the backend.

Legitimate fragments — `src`, `src/pkg`, `a/b/c`, internal-but-non-escaping
`a/../b`, and the empty fragment — continue to work unchanged.

## Tests

- **Unit** (`tests/unit/test_link.py`): valid fragments preserved; invalid ones
  rejected — traversal (both separators), absolute, drive-relative, UNC,
  percent-encoded traversal, and control-character/NUL payloads.
- **Unit** (`tests/unit/test_req_install.py`): the sink containment guard
  rejects an escaping value even when layer-1 validation is bypassed.
- **Functional** (`tests/functional/test_install_reqs.py`): the real pip CLI
  rejects traversal payloads at parse time; and the end-to-end regression test
  proves the build backend never executes outside the unpacked source tree.

Full unit suite: **1801 passed** (the only failures are 3 pre-existing,
environment-specific Windows cases that fail identically on the base, in files
this change does not touch). `ruff check`, `ruff format` (on changed code), and
`mypy` are clean.

## Files changed

- `src/pip/_internal/models/link.py` — fragment validation + `_path_escapes_root` helper
- `src/pip/_internal/req/req_install.py` — defense-in-depth containment check
- `src/pip/_internal/exceptions.py` — `InvalidSubdirectoryFragment` diagnostic
- `tests/unit/test_link.py`, `tests/unit/test_req_install.py`,
  `tests/functional/test_install_reqs.py` — coverage
- `news/subdirectory-fragment-path-traversal.bugfix.rst` — changelog
