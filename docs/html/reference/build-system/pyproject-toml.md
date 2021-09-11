# `pyproject.toml`

```{versionadded} 10.0

```

Modern Python packages can contain a `pyproject.toml` file, first introduced in
{pep}`518` and later expanded in {pep}`517`, {pep}`621` and {pep}`660`.
This file contains build system requirements and information, which is used by
pip to build the package.

## Build process

The overall process for building a package is:

- Create an isolated build environment.
- Populate the build environment with build dependencies.
- Generate the package's metadata, if necessary and possible.
- Generate a wheel for the package.

The wheel can then be used to perform an installation, if necessary.

### Build Isolation

For building packages using this interface, pip uses an _isolated environment_.
That is, pip will install build-time Python dependencies in a temporary
directory which will be added to `sys.path` for the build commands. This ensures
that build requirements are handled independently of the user's runtime
environment.

For example, a project that needs an older version of setuptools to build can
still be installed, even if the user has an newer version installed (and
without silently replacing that version).

### Build-time dependencies

Introduced in {pep}`518`, the `build-system.requires` key in the
`pyproject.toml` file is a list of requirement specifiers for build-time
dependencies of a package.

```toml
[build-system]
requires = ["setuptools ~= 58.0", "cython ~= 0.29.0"]
```

It is also possible for a build backend to provide dynamically calculated
build dependencies, using {pep}`517`'s `get_requires_for_build_wheel` hook. This
hook will be called by pip, and dependencies it describes will also be installed
in the build environment.

### Metadata Generation

```{versionadded} 19.0

```

Once the build environment has been created and populated with build-time
dependencies, `pip` will usually need metadata about a package (name, version,
dependencies, and more).

If {pep}`517`'s `prepare_metadata_for_build_wheel` hook is provided by the
build backend, that will be used to generate the packages' metadata. Otherwise,
a wheel will be generated (as described below) and the metadata contained
within such a wheel will be used.

### Wheel Generation

```{versionadded} 19.0

```

For generating a wheel, pip uses the {pep}`517`'s `build_wheel` hook that needs
to be provided by the build backend. The build backend may compile C/C++ code
at this point, depending on the package. Wheels generated using this mechanism
can be [cached](wheel-caching) for reuse, to speed up future installations.

### Editable Installation

This is currently not supported. However, this will be supported in the near
future, once {pep}`660` is implemented in pip.

## Build output

It is the responsibility of the build backend to ensure that the output is
in the correct encoding, as described in {pep}`517`. These likely involve
the same challenges as pip has for legacy builds.

## Fallback Behaviour

If a project does not have a `pyproject.toml` file containing a `build-system`
section, it will be assumed to have the following backend settings:

```toml
[build-system]
requires = ["setuptools>=40.8.0", "wheel"]
build-backend = "setuptools.build_meta:__legacy__"
```

If a project has a `build-system` section but no `build-backend`, then:

- It is expected to include `setuptools` and `wheel` as build requirements. An
  error is reported if the installed version of `setuptools` is not recent
  enough.

- The `setuptools.build_meta:__legacy__` build backend will be used.

## Disabling build isolation

This can be disabled using the `--no-build-isolation` flag -- users supplying
this flag are responsible for ensuring the build environment is managed
appropriately, including ensuring that all required build-time dependencies are
installed, since pip does not manage build-time dependencies when this flag is
passed.

## Historical notes

As this feature was incrementally rolled out, there have been various notable
changes and improvements in it.

- setuptools 40.8.0 is the first version of setuptools that offers a
  {pep}`517` backend that closely mimics directly executing `setup.py`.
- Prior to pip 18.0, pip only supports installing build requirements from
  wheels, and does not support the use of environment markers and extras (only
  version specifiers are respected).
- Prior to pip 18.1, build dependencies using `.pth` files are not properly
  supported; as a result namespace packages do not work under Python 3.2 and
  earlier.
