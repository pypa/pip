# Installation

pip is already installed if you are:

- working in a
  {ref}`virtual environment <pypug:Creating and using Virtual Environments>`
- using Python downloaded from [python.org](https://www.python.org)
- using Python that has not been modified by a redistributor to remove
  {mod}`ensurepip`

## Supported Methods

If your Python environment does not have pip installed, there are 2 mechanisms
to install pip supported directly by pip's maintainers:

- [Using ensurepip](#using-ensurepip)
- [Using get-pip.py](#using-get-pip-py)

### Using {mod}`ensurepip`

Python comes with an {mod}`ensurepip` module, which can install pip in a
Python environment.

To install pip using `ensurepip`, run:

```{pip-cli}
$ python -m ensurepip --upgrade
```

```{note}
It is strongly recommended to upgrade to the current version of pip using
`--upgrade` when calling ensurepip. It is possible to skip this flag, which
also means that the process would not access the internet.
```

More details about how {mod}`ensurepip` works and how it can be used, is
available in the standard library documentation.

### Using get-pip.py

`get-pip.py` is a Python script for installing pip in an environment. It uses
a bundled copy of pip to install pip.

To use `get-pip.py`, you'll want to:

- Download the `get-pip.py` script, from <https://bootstrap.pypa.io/get-pip.py>.

  On most Linux/MacOS machines, this can be done using the command:

  ```
  $ curl -sSL https://bootstrap.pypa.io/get-pip.py -o get-pip.py
  ```

- Open the terminal/command prompt on your OS, in the folder containing the
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

If you face issues when using Python installed using these mechanisms, it is
recommended to request for support from the relevant provider (eg: linux distro
community, cloud provider's support channels, etc).

## Compatibility

The current version of pip works on:

- Windows, Linux and MacOS.
- CPython 3.6, 3.7, 3.8, 3.9 and latest PyPy3.

pip is tested to work on the latest patch version of the Python interpreter,
for each of the minor versions listed above. Previous patch versions are
supported on a best effort approach.

pip's maintainers do not provide support for users on older versions of Python,
and these users should request for support from the relevant provider
(eg: linux distro community, cloud provider's support channels, etc).

[^python]: The `ensurepip` module was added to the Python standard library in Python 3.4.
