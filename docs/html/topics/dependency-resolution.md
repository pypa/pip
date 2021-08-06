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

You could try something like:

```{pip-cli}
$ pip install tea "cup >= 3.13"
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

## Dealing with dependency conflicts

This section provides practical suggestions to pip users who encounter
a `ResolutionImpossible` error, where pip cannot install their specified
packages due to conflicting dependencies.

### Understanding your error message

When you get a `ResolutionImpossible` error, you might see something
like this:

```{pip-cli}
$ pip install "pytest < 4.6" pytest-cov==2.12.1
[regular pip output]
ERROR: Cannot install pytest-cov==2.12.1 and pytest<4.6 because these package versions have conflicting dependencies.

The conflict is caused by:
    The user requested pytest<4.6
    pytest-cov 2.12.1 depends on pytest>=4.6
```

In this example, pip cannot install the packages requested because they are
asking for conflicting versions of pytest.

- `pytest-cov` version `2.12.1`, requires `pytest` with a version or equal to
  `4.6`.
- `package_tea` version `4.3.0` depends on version `2.3.1` of
  `package_water`

Sometimes these messages are straightforward to read, because they use
commonly understood comparison operators to specify the required version
(e.g. `<` or `>`).

However, Python packaging also supports some more complex ways for
specifying package versions (e.g. `~=` or `*`):

| Operator | Description                                                    | Example                                             |
| -------- | -------------------------------------------------------------- | --------------------------------------------------- |
| `>`      | Any version greater than the specified version.                | `>3.1`: any version greater than `3.1`.             |
| `<`      | Any version less than the specified version.                   | `<3.1`: any version less than `3.1`.                |
| `<=`     | Any version less than or equal to the specified version.       | `<=3.1`: any version less than or equal to `3.1`.   |
| `>=`     | Any version greater than or equal to the specified version.    | `>=3.1`: version `3.1` and greater.                 |
| `==`     | Exactly the specified version.                                 | `==3.1`: only `3.1`.                                |
| `!=`     | Any version not equal to the specified version.                | `!=3.1`: any version other than `3.1`.              |
| `~=`     | Any compatible{sup}`1` version.                                | `~=3.1`: any version compatible{sup}`1` with `3.1`. |
| `*`      | Can be used at the end of a version number to represent _all_. | `==3.1.*`: any version that starts with `3.1`.      |

{sup}`1` Compatible versions are higher versions that only differ in the final segment.
`~=3.1.2` is equivalent to `>=3.1.2, ==3.1.*`. `~=3.1` is equivalent to `>=3.1, ==3.*`.

The detailed specification of supported comparison operators can be
found in {pep}`440`.

### Possible solutions

The solution to your error will depend on your individual use case. Here
are some things to try:

#### Audit your top level requirements

As a first step, it is useful to audit your project and remove any
unnecessary or out of date requirements (e.g. from your `setup.py` or
`requirements.txt` files). Removing these can significantly reduce the
complexity of your dependency tree, thereby reducing opportunities for
conflicts to occur.

#### Loosen your top level requirements

Sometimes the packages that you have asked pip to install are
incompatible because you have been too strict when you specified the
package version.

In our first example both `package_coffee` and `package_tea` have been
_pinned_ to use specific versions
(`package_coffee==0.44.1b0 package_tea==4.3.0`).

To find a version of both `package_coffee` and `package_tea` that depend on
the same version of `package_water`, you might consider:

- Loosening the range of packages that you are prepared to install
  (e.g. `pip install "package_coffee>0.44.*" "package_tea>4.0.0"`)
- Asking pip to install _any_ version of `package_coffee` and `package_tea`
  by removing the version specifiers altogether (e.g.
  `pip install package_coffee package_tea`)

In the second case, pip will automatically find a version of both
`package_coffee` and `package_tea` that depend on the same version of
`package_water`, installing:

- `package_coffee 0.46.0b0`, which depends on `package_water 2.6.1`
- `package_tea 4.3.0` which _also_ depends on `package_water 2.6.1`

If you want to prioritize one package over another, you can add version
specifiers to _only_ the more important package:

```{pip-cli}
$ pip install package_coffee==0.44.1b0 package_tea
```

This will result in:

- `package_coffee 0.44.1b0`, which depends on `package_water 2.6.1`
- `package_tea 4.1.3` which also depends on `package_water 2.6.1`

Now that you have resolved the issue, you can repin the compatible
package versions as required.

#### Loosen the requirements of your dependencies

Assuming that you cannot resolve the conflict by loosening the version
of the package you require (as above), you can try to fix the issue on
your _dependency_ by:

- Requesting that the package maintainers loosen _their_ dependencies
- Forking the package and loosening the dependencies yourself

:::{warning}
If you choose to fork the package yourself, you are _opting out_ of
any support provided by the package maintainers. Proceed at your own risk!
:::

#### All requirements are appropriate, but a solution does not exist

Sometimes it's simply impossible to find a combination of package
versions that do not conflict. Welcome to [dependency hell].

In this situation, you could consider:

- Using an alternative package, if that is acceptable for your project.
  See [Awesome Python] for similar packages.
- Refactoring your project to reduce the number of dependencies (for
  example, by breaking up a monolithic code base into smaller pieces).

### Getting help

If none of the suggestions above work for you, we recommend that you ask
for help on:

- [Python user Discourse](https://discuss.python.org/c/users/7)
- [Python user forums](https://www.python.org/community/forums/)
- [Python developers Slack channel](https://pythondev.slack.com/)
- [Python IRC](https://www.python.org/community/irc/)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/python)

See ["How do I ask a good question?"] for tips on asking for help.

Unfortunately, **the pip team cannot provide support for individual
dependency conflict errors**. Please _only_ open a ticket on
[pip's issue tracker](https://github.com/pypa/pip/issues) if you believe
that your problem has exposed a bug in pip.

["how do i ask a good question?"]: https://stackoverflow.com/help/how-to-ask
[awesome python]: https://python.libhunt.com/
[dependency hell]: https://en.wikipedia.org/wiki/Dependency_hell
