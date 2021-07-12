# Getting Started

To get started with using pip, you should [install Python] on your system.

[install Python]: https://realpython.com/installing-python/

## Ensure you have a working pip

As a first step, you should check that you have a working Python with pip
installed. This can be done by running the following commands and making
sure that the output looks similar.

```{pip-cli}
$ python --version
Python 3.N.N
$ pip --version
pip X.Y.Z from ... (python 3.N.N)
```

If that worked, congratulations! You have a working pip in your environment.

If you got output that does not look like the sample above, please read
the {doc}`installation` page. It provides guidance on how to install pip
within a Python environment that doesn't have it.

## Common tasks

### Install a package

```{pip-cli}
$ pip install sampleproject
[...]
Successfully installed sampleproject
```

By default, pip will fetch packages from [Python Package Index][PyPI], a
repository of software for the Python programming language where anyone can
upload packages.

[PyPI]: https://pypi.org/

### Install a package from GitHub

```{pip-cli}
$ pip install git+https://github.com/pypa/sampleproject.git@main
[...]
Successfully installed sampleproject
```

See {doc}`topics/vcs-support` for more information about this syntax.

### Install a package from a distribution file

pip can install directly from distribution files as well. They come in 2 forms:

- {term}`source distribution <Source Distribution (or "sdist")>` (usually shortened to "sdist")
- {term}`wheel distribution <Wheel>` (usually shortened to "wheel")

```{pip-cli}
$ pip install sampleproject-1.0.tar.gz
[...]
Successfully installed sampleproject
$ pip install sampleproject-1.0-py3-none-any.whl
[...]
Successfully installed sampleproject
```

### Install multiple packages using a requirements file

Many Python projects use {file}`requirements.txt` files, to specify the
list of packages that need to be installed for the project to run. To install
the packages listed in that file, you can run:

```{pip-cli}
$ pip install -r requirements.txt
[...]
Successfully installed sampleproject
```

### Upgrade a package

```{pip-cli}
$ pip install --upgrade sampleproject
Uninstalling sampleproject:
   [...]
Proceed (y/n)? y
Successfully uninstalled sampleproject
```

### Uninstall a package

```{pip-cli}
$ pip uninstall sampleproject
Uninstalling sampleproject:
   [...]
Proceed (y/n)? y
Successfully uninstalled sampleproject
```

## Next Steps

It is recommended to learn about what virtual environments are and how to use
them. This is covered in the ["Installing Packages"](pypug:tutorials/installing-packages)
tutorial on packaging.python.org.
