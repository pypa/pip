# Repeatable Installs

pip can be used to achieve various levels of repeatable environments. This page
walks through increasingly stricter definitions of what "repeatable" means.

## Pinning the package versions

Pinning package versions of your dependencies in the requirements file
protects you from bugs or incompatibilities in newly released versions:

```
SomePackage == 1.2.3
DependencyOfSomePackage == 4.5.6
```

```{note}
Pinning refers to using the `==` operator to require the package to be a
specific version.
```

A requirements file, containing pinned package versions can be generated using
{ref}`pip freeze`. This would not only the top-level packages, but also all of
their transitive dependencies. Performing the installation using
{ref}`--no-deps <install_--no-deps>` would provide an extra dose of insurance
against installing anything not explicitly listed.

This strategy is easy to implement and works across OSes and architectures.
However, it trusts the locations you're fetching the packages from (like PyPI)
and the certificate authority chain. It also relies on those locations not
allowing packages to change without a version increase. (PyPI does protect
against this.)

## Hash-checking

Beyond pinning version numbers, you can add hashes against which to verify
downloaded packages:

```none
FooProject == 1.2 --hash=sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
```

This protects against a compromise of PyPI or the HTTPS certificate chain. It
also guards against a package changing without its version number changing (on
indexes that allow this). This approach is a good fit for automated server
deployments.

Hash-checking mode is a labour-saving alternative to running a private index
server containing approved packages: it removes the need to upload packages,
maintain ACLs, and keep an audit trail (which a VCS gives you on the
requirements file for free). It can also substitute for a vendored library,
providing easier upgrades and less VCS noise. It does not, of course,
provide the availability benefits of a private index or a vendored library.

[pip-tools] is a package that builds upon pip, and provides a good workflow for
managing and generating requirements files.

[pip-tools]: https://github.com/jazzband/pip-tools#readme

## Using a wheelhouse (AKA Installation Bundles)

{ref}`pip wheel` can be used to generate and package all of a project's
dependencies, with all the compilation performed, into a single directory that
can be converted into a single archive. This archive then allows installation
when index servers are unavailable and avoids time-consuming recompilation.

````{admonition} Example
Creating the bundle, on a modern Unix system:

```
$ tempdir=$(mktemp -d /tmp/wheelhouse-XXXXX)
$ python -m pip wheel -r requirements.txt --wheel-dir=$tempdir
$ cwd=`pwd`
$ (cd "$tempdir"; tar -cjvf "$cwd/bundled.tar.bz2" *)
```

Installing from the bundle, on a modern Unix system:

```
$ tempdir=$(mktemp -d /tmp/wheelhouse-XXXXX)
$ (cd $tempdir; tar -xvf /path/to/bundled.tar.bz2)
$ python -m pip install --force-reinstall --no-index --no-deps $tempdir/*
```
````

Note that such a wheelhouse contains compiled packages, which are typically
OS and architecture-specific, so these archives are not necessarily portable
across machines.

Hash-checking mode can also be used along with this method (since this uses a
requirements file as well), to ensure that future archives are built with
identical packages.

```{warning}
Beware of the `setup_requires` keyword arg in {file}`setup.py`. The (rare)
packages that use it will cause those dependencies to be downloaded by
setuptools directly, skipping pip's protections. If you need to use such a
package, see {ref}`Controlling setup_requires <controlling-setup-requires>`.
```
