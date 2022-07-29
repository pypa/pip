# Managing a different Python interpreter


Occasionally, you may want to use pip to manage a Python installation other than
the one pip is installed into. In this case, you can use the `--python` option
to specify the interpreter you want to manage. This option can take one of three
values:

1. The path to a Python executable.
2. The path to a virtual environment.
3. Either "py" or "python", referring to the currently active Python interpreter.

In all 3 cases, pip will run exactly as if it had been invoked from that Python
environment.

One example of where this might be useful is to manage a virtual environment
that does not have pip installed.

````{tab} Unix/macOS
```{code-block} console
$ python -m venv .venv --without-pip
$ python -m pip --python .venv install SomePackage
[...]
Successfully installed SomePackage
```
````
````{tab} Windows
```{code-block} console
C:\> py -m venv .venv --without-pip
C:\> py -m pip --python .venv install SomePackage
[...]
Successfully installed SomePackage
```
````

You could also use `--python .venv/bin/python` (or on Windows,
`--python .venv\Scripts\python.exe`) if you wanted to be explicit, but the
virtual environment name is shorter and works exactly the same.
