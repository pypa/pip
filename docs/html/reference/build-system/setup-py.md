# `setup.py` (legacy)

Prior to the introduction of pyproject.toml-based builds (in {pep}`517` and
{pep}`518`), pip had only supported installing packages using `setup.py` files
that were built using {pypi}`setuptools`.

The interface documented here is retained currently solely for legacy purposes,
until the migration to `pyproject.toml`-based builds can be completed.

```{caution}
The arguments and syntax of the various invocations of `setup.py` made by
pip, are considered an implementation detail that is strongly coupled with
{pypi}`setuptools`. This build system interface is not meant to be used by any
other build backend, which should be based on the {doc}`pyproject-toml` build
system interface instead.

Further, projects should _not_ expect to rely on there being any form of
backward compatibility guarantees around the `setup.py` interface.
```

## Build process

The overall process for building a package is:

- Generate the package's metadata.
- Generate a wheel for the package.

The wheel can then be used to perform an installation, if necessary.

### Metadata Generation

As a first step, `pip` needs to get metadata about a package (name, version,
dependencies, and more). It collects this by calling `setup.py egg_info`.

The `egg_info` command generates the metadata for the package, which pip can
then consume and proceed to gather all the dependencies of the package. Once
the dependency resolution process is complete, pip will proceed to the next
stage of the build process for these packages.

### Wheel Generation

When provided with a {term}`pypug:source distribution (or "sdist")` for a
package, pip will attempt to build a {term}`pypug:wheel`. Since wheel
distributions can be [cached](wheel-caching), this can greatly speed up future
installations for the package.

This is done by calling `setup.py bdist_wheel` which requires the {pypi}`wheel`
package to be installed.

If this wheel generation is successful (this can include compiling C/C++ code,
depending on the package), the generated wheel is added to pip's wheel cache
and will be used for this installation. The built wheel is cached locally
by pip to avoid repeated identical builds.

If this wheel generation fails, pip runs `setup.py clean` to clean up any build
artifacts that may have been generated. After that, pip will attempt a direct
installation.

### Editable Installation

For installing packages in "editable" mode
({ref}`pip install --editable <install_--editable>`), pip will invoke
`setup.py develop`, which will use setuptools' mechanisms to perform an
editable/development installation.

## Setuptools Injection

To support projects that directly use `distutils`, pip injects `setuptools` into
`sys.modules` before invoking `setup.py`. This injection should be transparent
to `distutils`-based projects.

## Customising the build

The `--global-option` and `--build-option` arguments to the `pip install`
and `pip wheel` inject additional arguments into the `setup.py` command
(`--build-option` is only available in `pip wheel`).

```{attention}
The use of `--global-option` and `--build-option` is highly setuptools
specific, and is considered more an accident of the current implementation than
a supported interface. It is documented here for completeness. These flags will
not be supported, once this build system interface is dropped.
```

These arguments are included in the command as follows:

```
python setup.py <global_options> BUILD COMMAND <build_options>
```

The options are passed unmodified, and presently offer direct access to the
distutils command line. For example:

```{pip-cli}
$ pip wheel --global-option bdist_ext --global-option -DFOO wheel
```

will result in pip invoking:

```
setup.py bdist_ext -DFOO bdist_wheel -d TARGET
```

This passes a preprocessor symbol to the extension build.

(build-output)=

## Build Output

Any output produced by the build system will be read by pip (for display to the
user if requested). In order to correctly read the build system output, pip
requires that the output is written in a well-defined encoding, specifically
the encoding the user has configured for text output (which can be obtained in
Python using `locale.getpreferredencoding`). If the configured encoding is
ASCII, pip assumes UTF-8 (to account for the behaviour of some Unix systems).

Build systems should ensure that any tools they invoke (compilers, etc) produce
output in the correct encoding. In practice - and in particular on Windows,
where tools are inconsistent in their use of the "OEM" and "ANSI" codepages -
this may not always be possible. pip will therefore attempt to recover cleanly
if presented with incorrectly encoded build tool output, by translating
unexpected byte sequences to Python-style hexadecimal escape sequences
(`"\x80\xff"`, etc). However, it is still possible for output to be displayed
using an incorrect encoding (mojibake).
