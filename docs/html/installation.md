# Installation

pip is already installed if you are:

- working in a
  [virtual environment](pypug:Creating\ and\ using\ Virtual\ Environments)
  created by [venv](pypug:venv) or [virtualenv](pypug:virtualenv).
- using Python, downloaded from [python.org](https://www.python.org).
- using Python, that has not been patched by a redistributor to remove
  `ensurepip`.

## Compatibility

The current version of pip works on:

- Windows, Linux/Unix and MacOS.
- CPython 3.6, 3.7, 3.8, 3.9 and latest PyPy3.

pip is tested to work on the latest patch version of the Python interpreter,
for each of the minor versions listed above. Previous patch versions are
supported on a best effort approach.

```{note}
If you're using an older version of pip or Python, it is possible that
the instructions on this page will not work for you.

pip's maintainers would not be able to provide support for users on such
older versions, and these users are advised to reach out to the
providers of those older versions of pip/Python (eg: your vendor or
Linux distribution) for support.
```

### Using {mod}`ensurepip`

Python >= 3.4 can self-bootstrap pip with the built-in {mod}`ensurepip` module.
To install pip using {mod}`ensurepip`, run:

```{pip-cli}
$ python -m ensurepip --upgrade
```

```{note}
It is strongly recommended to upgrade to the current version of pip using
`--upgrade` when calling ensurepip. It is possible to skip this flag, which
also means that the process would not access the internet.
```

More details about how {mod}`ensurepip` works and can be used, is available in
the standard library documentation.

### Using get-pip.py

`get-pip.py` is a bootstrapper script, that is capable of installing pip in an
environment. To install pip using `get-pip.py`, you'll want to:

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
