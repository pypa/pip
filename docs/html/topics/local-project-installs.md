# Local project installs

It is extremely common to have a project, available in a folder/directory on your computer [^1] that you wish to install.

With pip, depending on your usecase, there are two ways to do this:

- A regular install
- An editable install

## Regular installs

You can install local projects by specifying the project path to pip:

```{pip-cli}
$ pip install path/to/SomeProject
```

This will install the project into the Python that pip is associated with, in a manner similar to how it would actually be installed.

This is what should be used in CI system and for deployments, since it most closely mirrors how a package would get installed if you build a distribution and installed from it (because that's _exactly_ what it does).

(editable-installs)=

## Editable installs

You can install local projects in "editable" mode:

```{pip-cli}
$ pip install -e path/to/SomeProject
```

Editable installs allow you to install your project without copying any files. Instead, the files in the development directory are added to Python's import path. This approach is well suited for development and is also known as a "development installation".

With an editable install, you only need to perform a re-installation if you change the project metadata (eg: version, what scripts need to be generated etc). You will still need to run build commands when you need to perform a compilation for non-Python code in the project (eg: C extensions).

```{caution}
It is possible to see behaviour differences between regular installs vs editable installs. These differences depend on the build-backend, and you should check the build-backend documentation for the details. In case you distribute the project as a "distribution package", users will see the behaviour of regular installs -- thus, it is important to ensure that regular installs work correctly.
```

```{note}
This is functionally the same as [setuptools' develop mode], and that's precisely the mechanism used for setuptools-based projects.

There are two advantages over using `setup.py develop` directly:

- This works with non-setuptools build-backends as well.
- The ".egg-info" directory is created relative to the project path, when using pip. This is generally a better location than setuptools, which dumps it in the current working directory.
```

[setuptools' develop mode]: https://setuptools.readthedocs.io/en/latest/userguide/development_mode.html

## Build artifacts

```{versionchanged} 21.3
The project being installed is no longer copied to a temporary directory before invoking the build system, by default. A `--use-deprecated=out-of-tree-build` option is provided as a temporary fallback to aid user migrations.
```

```{versionchanged} 22.1
The `--use-deprecated=out-of-tree-build` option has been removed.
```

When provided with a project that's in a local directory, pip will invoke the build system "in place". This behaviour has several consequences:

- Local project builds will now be significantly faster, for certain kinds of projects and on systems with slow I/O (eg: via network attached storage or overly aggressive antivirus software).
- Certain build backends (eg: `setuptools`) will litter the project directory with secondary build artifacts (eg: `.egg-info` directories).
- Certain build backends (eg: `setuptools`) may not be able to perform with parallel builds anymore, since they previously relied on the fact that pip invoked them in a separate directory for each build.

[^1]: Specifically, the current machine's filesystem.
