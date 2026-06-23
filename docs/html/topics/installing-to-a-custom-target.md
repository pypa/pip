(install-target)=
# Installing to a custom location

Sometimes you want to install packages into a directory that is not the
standard site-packages location for the Python interpreter that pip is
associated with — for example, when packaging a vendored distribution,
testing a project against a local checkout, or laying out a sandbox
Python tree without modifying the system environment.

The [`pip install`](https://pip.pypa.io/en/stable/cli/pip_install/) command
provides the `--target` (short form: `-t`) option for exactly this case.
It takes a path to an existing directory and installs every distribution
plus its dependencies into that directory, organized the same way that
they would be in `site-packages`.

```{pip-cli}
$ pip install --target ./my-libs SomePackage
```

After the command above, `./my-libs/SomePackage` and the related
distribution metadata exist together with their dependencies under
`./my-libs/`, and Python can be pointed at the directory with `PYTHONPATH`:

```{pip-cli}
$ PYTHONPATH=./my-libs python -c "import SomePackage"
```

## How it differs from `--user`

{ref}`--user <install_--user>` installs into the per-user site-packages
directory under your home folder (`~/.local/` on Linux and macOS,
`%APPDATA%\Python` on Windows). It is intended for the simple case where
you want packages available to your normal user account without
touching the system interpreter. `--target` is intended for *any*
directory, including one that has nothing to do with any Python
interpreter installed on the machine, and pip will not try to manage
`easy-install.pth` or user-level site configuration for it.

The two options cannot be combined. Running `pip install --user --target
./my-libs` raises an error, because the user site-packages directory and
the target directory are different concepts and pip will not guess
which one should win.

## When to use `--upgrade` with `--target`

By default pip will not overwrite an already-installed distribution in
the target directory. If you are rebuilding the contents of `--target`
frequently (for example, refreshing a CI artifact), combine it with
{ref}`--upgrade <install_--upgrade>` to make pip replace existing
packages with newer versions:

```{pip-cli}
$ pip install --upgrade --target ./my-libs SomePackage
```

Without `--upgrade`, repeated installs into the same target directory
silently keep whichever distribution was first written into the
directory. This is intentional — it lets you place a hand-curated set
of packages into the target and have pip leave them alone — but it can
be surprising if you expected `--target` to behave like a regular
install.

## Caveats

- `--target` is mutually exclusive with `--user` (described above) and
  with {ref}`--root <install_--root>`. Combining them raises an error.

- pip does not record target installs in `importlib.metadata` for the
  current interpreter, because the target directory may not be on its
  import path. To use installed packages from a target directory, add
  it to `sys.path` explicitly, for example by setting `PYTHONPATH` or
  by extending `sys.path` in a custom launcher.

- `--target` is not a substitute for a virtual environment. It manages
  a flat directory, not an isolated environment with its own interpreter
  metadata; dependency resolution in particular has no protection
  against global state on the host in this mode.

For the full list of related options, see the
[`pip install`](https://pip.pypa.io/en/stable/cli/pip_install/)
reference page.
