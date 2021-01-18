# User Installs

In Python 2.6, a ["user scheme"][python-user-scheme] was added. This provided
an alternative install location for Python packages that is (as the name
suggests) user-specific.

[python-user-scheme]: https://docs.python.org/3/install/index.html#alternate-installation-the-user-scheme

This allows users to install packages in a location where they will have the
required filesystem permissions to do so and to avoid modifying a interpreter's
`site-packages` which might be used by other users (on shared machines) or other
programs (like their OS's programs on Linux).

```{important}
This mechanism does not substitute the use of virtual environments, which are
mainly for isolating the dependency graphs across multiple projects *and*
(optionally) for isolating from the interpreter's `site-packages`.
```

## How it works

pip supports installing into the user scheme and does so automatically when the
user does not have write permissions to the per-interpreter `site-packages`
folder (which is the default). It is also possible to force this behaviour,
by passing the [`--user`](install_--user) flag to `pip install`.

`pip install --user` follows four rules:

1. When globally installed packages are on the python path, and they *conflict*
   with the installation requirements, they are ignored, and *not*
   uninstalled.
2. When globally installed packages are on the python path, and they *satisfy*
   the installation requirements, pip does nothing, and reports that
   requirement is satisfied (similar to how global packages can satisfy
   requirements when installing packages in a `--system-site-packages`
   virtualenv).
3. pip will not perform a `--user` install in a `--no-site-packages`
   virtualenv (i.e. the default kind of virtualenv), due to the user site not
   being on the python path.  The installation would be pointless.
4. In a `--system-site-packages` virtualenv, pip will not install a package
   that conflicts with a package in the virtualenv site-packages.  The --user
   installation would lack sys.path precedence and be pointless.

## Examples

### With a virtual environment

In a `--no-site-packages` virtual environment (i.e. the default kind):

```{pip-cli} in-a-venv
$ pip install --user SomePackage
Can not perform a '--user' install. User site-packages are not visible in this virtual environment.
```

In a `--system-site-packages` virtual environment where `SomePackage==0.3`
is already installed in the virtual environment:

```{pip-cli} in-a-venv
$ pip install --user SomePackage==0.4
Will not install to the user site because it will lack sys.path precedence.
```

### Without a virtual environment

`SomePackage` is *not* installed globally:

```{pip-cli}
$ pip install --user SomePackage
[...]
Successfully installed SomePackage
```

`SomePackage` *is* installed globally, but is *not* the latest version:

```{pip-cli}
$ pip install --user SomePackage
[...]
Requirement already satisfied (use --upgrade to upgrade)
$ pip install --user --upgrade SomePackage
[...]
Successfully installed SomePackage
```

`SomePackage` *is* installed globally, and is the latest version:

```{pip-cli}
$ pip install --user SomePackage
[...]
Requirement already satisfied
$ pip install --user --upgrade SomePackage
[...]
Requirement already up-to-date: SomePackage
```
