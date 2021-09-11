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
: Standards-backed interface, that has build isolation and explicit declaration
  of build dependencies.

[`setup.py` based](setup-py)
: Legacy interface, that we're working to migrate users away from. Has no build
  isolation and no good mechanisms to declare build dependencies.
<!-- prettier-ignore-end -->

Details on the individual interfaces can be found on their dedicated pages,
linked above. This document covers the nuances around which build system
interface pip will use for a project, as well as details that apply all
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
Building wheel for pip (PEP 517)... done
```

```none
Building wheel for pip (setup.py)... done
```

Here, "PEP 517" refers to `pyproject.toml` based builds and "setup.py" refers
to `setup.py` based builds.

## Controlling which build system interface is used

It is possible to control which build system interface is used by pip, using
the [`--use-pep517`](install_--use-pep517) / `--no-use-pep517` flags (and
corresponding environment variable: `PIP_USE_PEP517`).

(controlling-setup_requires)=

## Controlling `setup_requires`

```{hint}
This is only relevant for projects that use setuptools as the build backend,
and use the `setup_requires` keyword argument in their setup.py file.
```

The `setup_requires` argument in `setup.py` is used to specify build-time
dependencies for a package. This has been superceded by `build-system.requires`
key in `pyproject.toml` files (per {pep}`518`). However, there are situations
where you might encounter a package that uses that argument (eg: the package
has not been updated to use the newer approach yet!).

Older versions of setuptools (`< 52.0`) use `easy_install` to try to fulfill
those dependencies, which can result in weird failures such as attempting to
install incompatible package versions or improper installation of such
dependencies.

Usually, the best solution for dealing with packages with `setup_requires` is
to install the packages listed in `setup_requires` beforehand, using a prior
`pip install` command. This is because there is no way to control how these
dependencies are located by `easy_install`, or how setuptools will invoke `pip`
using pip's command line options -- which makes it tricky to get things working
appropriately.

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

[distutils-config]: https://docs.python.org/3/install/index.html#distutils-configuration-files
