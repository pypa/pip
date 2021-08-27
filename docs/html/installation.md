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
- [`get-pip.py`](#get-pip-py)

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

Upgrading your `pip` by running:

```{pip-cli}
$ pip install --upgrade pip
```

(compatibility-requirements)=

## Compatibility

The current version of pip works on:

- Windows, Linux and MacOS.
- CPython 3.6, 3.7, 3.8, 3.9, 3.10 and latest PyPy3.

pip is tested to work on the latest patch version of the Python interpreter,
for each of the minor versions listed above. Previous patch versions are
supported on a best effort approach.

pip's maintainers do not provide support for users on older versions of Python,
and these users should request for support from the relevant provider
(eg: Linux distro community, cloud provider support channels, etc).

[^python]: The `ensurepip` module was added to the Python standard library in Python 3.4.
