# Dependency Resolution

pip is capable of determining and installing the dependencies of packages. The
process of determining which version of a dependency to install is known as
dependency resolution. This behaviour can be disabled by passing
{any}`--no-deps` to {any}`pip install`.

## How it works

When a user does a `pip install` (e.g. `pip install tea`), pip needs to work
out the package's dependencies (e.g. `spoon`, `hot-water`, `tea-leaves` etc.)
and what the versions of each of those dependencies it should install.

At the start of a `pip install` run, pip does not have all the dependency
information of the requested packages. It needs to work out the dependencies
of the requested packages, the dependencies of those dependencies, and so on.
Over the course of the dependency resolution process, pip will need to download
distribution files of the packages which are used to get the dependencies of a
package.

## Backtracking

```{versionchanged} 20.3
pip's dependency resolver is now capable of backtracking.
```

During dependency resolution, pip needs to make assumptions about the package
versions it needs to install and, later, check these assumptions were not
incorrect. When pip finds that an assumption it made earlier is incorrect, it
has to backtrack, which means also discarding some of the work that has already
been done, and going back to choose another path.

This can look like pip downloading multiple versions of the same package,
since pip explicitly presents each download to the user. The backtracking of
choices made during is not unexpected behaviour or a bug. It is part of how
dependency resolution for Python packages works.

````{admonition} Example
The user requests `pip install tea`. The package `tea` declares a dependency on
`hot-water`, `spoon`, `cup`, amongst others.

pip starts by picking the most recent version of `tea` and get the list of
dependencies of that version of `tea`. It will then repeat the process for
those packages, picking the most recent version of `spoon` and then `cup`. Now,
pip notices that the version of `cup` it has chosen is not compatible with the
version of `spoon` it has chosen. Thus, pip will "go back" (backtrack) and try
to use another version of `cup`. If it is successful, it will continue onto the
next package (like `sugar`). Otherwise, it will continue to backtrack on `cup`
until it finds a version of `cup` that is compatible with all the other
packages.

This can look like:

```console
$ pip install tea
Collecting tea
  Downloading tea-1.9.8-py2.py3-none-any.whl (346 kB)
     |████████████████████████████████| 346 kB 10.4 MB/s
Collecting spoon==2.27.0
  Downloading spoon-2.27.0-py2.py3-none-any.whl (312 kB)
     |████████████████████████████████| 312 kB 19.2 MB/s
Collecting cup>=1.6.0
  Downloading cup-3.22.0-py2.py3-none-any.whl (397 kB)
     |████████████████████████████████| 397 kB 28.2 MB/s
INFO: pip is looking at multiple versions of this package to determine
which version is compatible with other requirements.
This could take a while.
  Downloading cup-3.21.0-py2.py3-none-any.whl (395 kB)
     |████████████████████████████████| 395 kB 27.0 MB/s
  Downloading cup-3.20.0-py2.py3-none-any.whl (394 kB)
     |████████████████████████████████| 394 kB 24.4 MB/s
  Downloading cup-3.19.1-py2.py3-none-any.whl (394 kB)
     |████████████████████████████████| 394 kB 21.3 MB/s
  Downloading cup-3.19.0-py2.py3-none-any.whl (394 kB)
     |████████████████████████████████| 394 kB 26.2 MB/s
  Downloading cup-3.18.0-py2.py3-none-any.whl (393 kB)
     |████████████████████████████████| 393 kB 22.1 MB/s
  Downloading cup-3.17.0-py2.py3-none-any.whl (382 kB)
     |████████████████████████████████| 382 kB 23.8 MB/s
  Downloading cup-3.16.0-py2.py3-none-any.whl (376 kB)
     |████████████████████████████████| 376 kB 27.5 MB/s
  Downloading cup-3.15.1-py2.py3-none-any.whl (385 kB)
     |████████████████████████████████| 385 kB 30.4 MB/s
INFO: pip is looking at multiple versions of this package to determine
which version is compatible with other requirements.
This could take a while.
  Downloading cup-3.15.0-py2.py3-none-any.whl (378 kB)
     |████████████████████████████████| 378 kB 21.4 MB/s
  Downloading cup-3.14.0-py2.py3-none-any.whl (372 kB)
     |████████████████████████████████| 372 kB 21.1 MB/s
```

These multiple `Downloading cup-{version}` lines show that pip is backtracking
choices it is making during dependency resolution.
````

If pip starts backtracking during dependency resolution, it does not know how
many choices it will reconsider, and how much computation would be needed.

For the user, this means it can take a long time to complete when pip starts
backtracking. In the case where a package has a lot of versions, arriving at a
good candidate can take a lot of time. The amount of time depends on the
package size, the number of versions pip must try, and various other factors.

Backtracking reduces the risk that installing a new package will accidentally
break an existing installed package, and so reduces the risk that your
environment gets messed up. To do this, pip has to do more work, to find out
which version of a package is a good candidate to install.

## Possible ways to reduce backtracking

There is no one-size-fits-all answer to situations where pip is backtracking
excessively during dependency resolution. There are ways to reduce the
degree to which pip might backtrack though. Nearly all of these approaches
require some amount of trial and error.

### Allow pip to complete its backtracking

In most cases, pip will complete the backtracking process successfully.
This could take a very long time to complete, so this may not be your
preferred option.

However, it is a possible that pip will not be able to find a set of
compatible versions. For this, pip will try every possible combination that
it needs to and determine that there is no compatible set.

If you'd prefer not to wait, you can interrupt pip (Ctrl+c) and try the
strategies listed below.

### Reduce the number of versions pip is trying to use

It is usually a good idea to add constraints the package(s) that pip is backtracking on (e.g. in the above example - `cup`).

You could try:

```
pip install tea "cup >= 3.13"
```

This will reduce the number of versions of `cup` it tries, and
possibly reduce the time pip takes to install.

There is a possibility that the addition constraint is incorrect. When this
happens, the reduced search space makes it easier for pip to more quickly
determine what caused the conflict and present that to the user. It could also
result in pip backtracking on a different package due to some other conflict.

### Use constraint files or lockfiles

This option is a progression of the previous section. It requires users to know
how to inspect:

- the packages they're trying to install
- the package release frequency and compatibility policies
- their release notes and changelogs from past versions

During deployment, you can create a lockfile stating the exact package and
version number for for each dependency of that package. You can create this
with `pip-tools <https://github.com/jazzband/pip-tools/>`\_\_.

This means the "work" is done once during development process, and thus
will avoid performing dependency resolution during deployment.
