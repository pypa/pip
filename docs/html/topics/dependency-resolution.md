# Dependency Resolution

Pip is capable of determining and installing the dependencies of packages. The
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

## Yanked releases

An index can mark a release as yanked when a project detects that it might be broken. Yanking is a non-destructive alternative to deleting a release: it discourages inadvertent installations while leaving the release available to users who have pinned that version. Any Python package index that implements the yanking specification can provide this behavior.

During dependency resolution, pip ignores yanked releases when a non-yanked
version satisfies the requirements. If an exact version pin (for example,
`package==1.2.3`) can only be satisfied by yanked releases, pip can still install
one and warns that the selected version is yanked. The warning includes the
reason provided by the project, when one is available.

For more information, see the
[File yanking specification](https://packaging.python.org/en/latest/specifications/file-yanking/)
and [PyPI's guide to yanking releases](https://docs.pypi.org/project-management/yanking/).

## Backtracking

```{versionchanged} 20.3
Pip's dependency resolver is now capable of backtracking.
```

During dependency resolution, pip needs to make assumptions about the package
versions it needs to install and, later, check these assumptions were not
incorrect. When pip finds that an assumption it made earlier is incorrect, it
has to backtrack, which means also discarding some of the work that has already
been done, and going back to choose another path.

This can look like pip downloading multiple versions of the same package,
since pip explicitly presents each download to the user. The backtracking of
choices made during this step is not unexpected behaviour or a bug. It is part
of how dependency resolution for Python packages works.

````{admonition} Example
The user requests `pip install tea`. The package `tea` declares a dependency on
`hot-water`, `spoon`, `cup`, amongst others.

Pip starts by picking the most recent version of `tea` and gets the list of
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
