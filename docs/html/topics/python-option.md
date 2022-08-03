# Managing a different Python interpreter

```{versionadded} 22.3
```

Occasionally, you may want to use pip to manage a Python installation other than
the one pip is installed into. In this case, you can use the `--python` option
to specify the interpreter you want to manage. This option can take one of two
values:

1. The path to a Python executable.
2. The path to a virtual environment.

In both cases, pip will run exactly as if it had been invoked from that Python
environment.

One example of where this might be useful is to manage a virtual environment
that does not have pip installed.

```{pip-cli}
$ python -m venv .venv --without-pip
$ pip --python .venv install SomePackage
[...]
Successfully installed SomePackage
```

You could also use `--python .venv/bin/python` (or on Windows,
`--python .venv\Scripts\python.exe`) if you wanted to be explicit, but the
virtual environment name is shorter and works exactly the same.
