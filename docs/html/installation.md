# Installation

Usually, pip is automatically installed if you are:

- working in a
  {ref}`virtual environment <pypug:Creating and using Virtual Environments>`
- using Python downloaded from [python.org](https://www.python.org)
- using Python that has not been modified by a redistributor to remove
  {mod}`ensurepip`

## Supported Methods

If your Python environment does not have pip installed, there are 2 mechanisms
to install pip supported directly by pip's maintainers:

- [`ensurepip`](#ensurepip)
- [`get-pip.py`](#get-pippy)

### `ensurepip`

Python comes with an {mod}`ensurepip` module[^python], which can install pip in
a Python environment.

```{pip-cli}
$ python -m ensurepip --upgrade
```

More details about how {mod}`ensurepip` works and how it can be used, is
available in the standard library documentation.

### `get-pip.py`

This is a Python script that uses some bootstrapping logic to install
pip.

- Download the script, from <https://bootstrap.pypa.io/get-pip.py>.
- Open a terminal/command prompt, `cd` to the folder containing the
  `get-pip.py` file and run:

  ```{pip-cli}
  $ python get-pip.py
  ```

More details about this script can be found in [pypa/get-pip]'s README.

[pypa/get-pip]: https://github.com/pypa/get-pip

### Standalone zip application

```{note}
The zip application is currently experimental. We test that pip runs correctly
in this form, but it is possible that there could be issues in some situations.
We will accept bug reports in such cases, but for now the zip application should
not be used in production environments.
```

In addition to installing pip in your environment, pip is available as a
standalone [zip application](https://docs.python.org/3.11/library/zipapp.html).
This can be downloaded from <https://bootstrap.pypa.io/pip/pip.pyz>. There are
also zip applications for specific pip versions, named `pip-X.Y.Z.pyz`.

The zip application can be run using any supported version of Python:

```{pip-cli}
$ python pip.pyz --help
```

If run directly:

```{pip-cli}
$ pip.pyz --help
```

then the currently active Python interpreter will be used.

## Alternative Methods

Depending on how you installed Python, there might be other mechanisms
available to you for installing pip such as
{ref}`using Linux package managers <pypug:installing pip/setuptools/wheel with linux package managers>`.

These mechanisms are provided by redistributors of pip, who may have modified
pip to change its behaviour. This has been a frequent source of user confusion,
since it causes a mismatch between documented behaviour in this documentation
and how pip works after those modifications.

If you face issues when using Python and pip installed using these mechanisms,
it is recommended to request for support from the relevant provider (eg: Linux
distro community, cloud provider support channels, etc).

## Upgrading `pip`

Upgrade your `pip` by running:

```{pip-cli}
$ pip install --upgrade pip
```

(compatibility-requirements)=

## Compatibility

The current version of pip works on:

- Windows, Linux and MacOS.
- CPython 3.7, 3.8, 3.9, 3.10 and latest PyPy3.

pip is tested to work on the latest patch version of the Python interpreter,
for each of the minor versions listed above. Previous patch versions are
supported on a best effort approach.

Other operating systems and Python versions are not supported by pip's
maintainers.

Users who are on unsupported platforms should be aware that if they hit issues, they may have to resolve them for themselves. If they received pip from a source which provides support for their platform, they should request pip support from that source.

[^python]: The `ensurepip` module was added to the Python standard library in Python 3.4.
