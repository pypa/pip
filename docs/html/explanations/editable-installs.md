# Editable Installs

Editable installs are a mechanism to circumvent the need of (re)installing a
package on every change during development. With an editable install, changes
made to the package source (in its checkout directory) will be reflected in the
package visible to Python, without needing a reinstall.

pip only supports editable installs via [setuptools's "development mode"][1]
installs. You can install local projects or VCS projects in "editable" mode:

```{pip-cli}
$ pip install -e path/to/SomeProject
$ pip install -e git+http://repo/my_project.git#egg=SomeProject
```

For local projects, the "SomeProject.egg-info" directory is created relative to
the project path. This is one advantage over just using ``setup.py develop``,
which creates the "egg-info" directly relative the current working directory.

```{seealso}
{ref}`VCS Support` section for more information on VCS-related syntax.
```

```{important}
As of 30 Dec 2020, PEP 517 does not support editable installs. Various members
of the Python community are working on a new standard to [address this
limitation](https://discuss.python.org/t/4098).
```

[1]: https://setuptools.readthedocs.io/en/latest/userguide/development_mode.html#development-mode
