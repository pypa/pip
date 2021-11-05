(build-interface)=

# Build System Interface

When dealing with installable source distributions of a package, pip does not
directly handle the build process for the package. This responsibility is
delegated to "build backends" -- also known as "build systems". This means
that pip needs an interface, to interact with these build backends.

There are two main interfaces that pip uses for these interactions:

```{toctree}
:hidden:

pyproject-toml
setup-py
```

<!-- prettier-ignore-start -->
[`pyproject.toml` based](pyproject-toml)
: Standards-backed interface, that has explicit declaration and management of
  build dependencies.

[`setup.py` based](setup-py)
: Legacy interface, that we're working to migrate users away from. Has no good
  mechanisms to declare build dependencies.
<!-- prettier-ignore-end -->

Details on the individual interfaces can be found on their dedicated pages,
linked above. This document covers the nuances around which build system
interface pip will use for a project, as well as details that apply to all
the build system interfaces that pip may use.

## Determining which build system interface is used

Currently, pip uses the `pyproject.toml` based build system interface, if a
`pyproject.toml` file exists. If not, the legacy build system interface is used.
The intention is to switch to using the `pyproject.toml` build system interface
unconditionally and to drop support for the legacy build system interface at
some point in the future.

When performing a build, pip will mention which build system interface it is
using. Typically, this will take the form of a message like:

```none
Building wheel for pip (pyproject.toml)... done
```

```none
Building wheel for pip (setup.py)... done
```

The content in the brackets, refers to which build system interface is being
used.

```{versionchanged} 21.3
The output uses "pyproject.toml" instead of "PEP 517" to refer to be
`pyproject.toml` based build system interface.
```

## Controlling which build system interface is used

The [`--use-pep517`](install_--use-pep517) flag (and corresponding environment
variable: `PIP_USE_PEP517`) can be used to force all packages to build using
the `pyproject.toml` based build system interface. There is no way to force
the use of the legacy build system interface.

(controlling-setup_requires)=

## Controlling `setup_requires`

```{hint}
This is only relevant for projects that use setuptools as the build backend,
and use the `setup_requires` keyword argument in their setup.py file.
```

The `setup_requires` argument in `setup.py` is used to specify build-time
dependencies for a package. This has been superseded by the
`build-system.requires` key in `pyproject.toml` files (per {pep}`518`).
However, there are situations where you might encounter a package that uses
`setup_requires` (eg: the package has not been updated to use the newer
approach yet!).

If you control the package, consider adding a `pyproject.toml` file to utilise
the modern build system interface. That avoids invoking the problematic
behaviour by deferring to pip for the installations.

For the end users, the best solution for dealing with packages with
`setup_requires` is to install the packages listed in `setup_requires`
beforehand, using a prior `pip install` command. This is because there is no
way to control how these dependencies are located by `easy_install`, or how
setuptools will invoke `pip` using pip's command line options -- which makes it
tricky to get things working appropriately.

If you wish to ensure that `easy_install` invocations do not reach out to PyPI,
you will need to configure its behaviour using a
[`distutils` configuration file][distutils-config]. Here are some examples:

- To have the dependency located at an alternate index with `easy_install`

  ```ini
  [easy_install]
  index_url = https://my.index-mirror.com
  ```

- To have the dependency located from a local directory and not crawl PyPI, add this:

  ```ini
  [easy_install]
  allow_hosts = ''
  find_links = file:///path/to/local/archives/
  ```

```{admonition} Historical context
`setuptools < 52.0` will use `easy_install` to try to fulfill `setup_requires`
dependencies, which can result in weird failures -- `easy_install` does not
understand many of the modern Python packaging standards, and will usually
attempt to install incompatible package versions or to build packages
incorrectly. It also generates improper script wrappers, which don't do the
right thing in many situations.

Newer versions of `setuptools` will use `pip` for these installations, but have
limited ability to pass through any command line arguments. This can also result
in weird failures and subtly-incorrect behaviour.
```

[distutils-config]: https://docs.python.org/3/install/index.html#distutils-configuration-files
