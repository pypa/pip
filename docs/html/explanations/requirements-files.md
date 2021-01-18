# Requirements files

Requirements files contain a list of items to be installed using
{ref}`pip install`.

```
pip install -r requirements.txt
```

Details on the format of the files are here: {ref}`Requirements File Format`.
Logically, a requirements file is just a list of {ref}`pip install` arguments
placed in a file. You should not rely on the items in the file being installed
by pip in any particular order.

## What requirements files are for

```{seealso}
Donald Stufft's article on ["setup.py vs requirements.txt"][setup-vs-req]
discusses an important concept: "abstract" vs "concrete" dependencies.
```

[setup-vs-req]: https://caremad.io/2013/07/setup-vs-requirement/

### Repeatable installs

Requirements files can be used to hold the result from {ref}`pip freeze` for the
purpose of achieving {ref}`repeatable installations <repeatable-installs>`.

In this case, your requirements file contains a pinned version of everything
that was installed when `pip freeze` was run.

```
pip freeze > requirements.txt
pip install -r requirements.txt
```

### Forcing an alternate version of a subdependency

Requirements files can be used to force pip to install an alternate version of a
sub-dependency.

For example, suppose `ProjectA` in your requirements file requires `ProjectB`,
but the latest version (v1.3) has a bug, you can force pip to accept earlier
versions like so::

```
ProjectA
ProjectB < 1.3
```

### Overriding a dependencies with a patched variant

Requirements files can be used to override a dependency, with a patched variant
that lives in version control.

For example, suppose a dependency `SomeDependency` from PyPI has a bug, and
you can't wait for an upstream fix. You could clone/copy the source code, make
the fix, and place it in a VCS with the tag `sometag`. It is now possible to
reference it in your requirements file with a line like:

```
git+https://myvcs.com/some_dependency@sometag#egg=SomeDependency
```

```{note}
* If `SomeDependency` was previously a "top-level" requirement in your
  requirements file (i.e. directly mentioned), then **replace** that with the
  new line referencing the VCS variant.
* If `SomeDependency` is a sub-dependency, then **add** the new line.
```

### Forcing pip to resolve dependencies a certain way

Requirements files were used to force pip to properly resolve dependencies.
This was especially relevant in pip 20.2 and earlier, which [did not have true
dependency resolution][gh-988]. The dependency resolution process in those
versions "simply" used the first specification it found for a package.

Note that pip determines package dependencies using a package's
[`Requires-Dist` metadata][requires-dist], not by discovering/looking for
`requirements.txt` files embedded in them.

[gh-988]: https://github.com/pypa/pip/issues/988
[requires-dist]: https://packaging.python.org/specifications/core-metadata/#requires-dist-multiple-use
