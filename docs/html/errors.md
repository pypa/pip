# Error Index

Inspired by the [Rust Compiler Error Index], this page describes the various
errors that may be presented by `sphinx-theme-builder`, indicating known causes
as well as potential solutions.

<!--
  Editor's note: Ensure that each error has a "What you can do" part to it.
-->

[rust compiler error index]: https://doc.rust-lang.org/error-index.html

## Pip Errors

Generic pip errors do not contain links to this page.

## Diagnostic Pip Errors

Diagnositic pip errors contain links to this page.

### externally-managed-environment

An `externally-managed-environment` error occurs when your operating system (OS) prevents you from using pip to install packages directly into the system-wide Python environment. This restriction was introduced via PEP 668 to prevent users from accidentally breaking OS-level tools that rely on a specific version of Python.

**What you can do:**

There are three standard ways to resolve this, depending on your goal: First, use a Virtual Environment. Second, use pipx if you want to install a tool for use from the command line. Lastly, if you absolutely must install a package system-wide and understand the risks of breaking your OS, then you can bypass the check by adding the specific flag: `--break-system-packages` to the pip install command.

### failed-build-dependency-install

A `failed-build-dependency-install` error typically means pip cannot find or compile the libraries necessary to complete the installation of the dependency.

**What you can do:**

Check that the python version is compatible with the version of the python dependency you are attempting to install. Upgrading pip with the `pip install --upgrade pip` command will often resolve failed builds. Check the documentation of the dependency for whether C/C++ compilers are needed to properly install the dependency.

### failed-wheel-build-for-install

When pip cannot find a wheel file for a dependency, pip tries to build the wheel from the source. If building the wheel from source fails, this error is raised.

**What you can do:**
Building the wheel can fail for many different reasons. First, you can check that the version of python is compatible with your dependencies. Next, you can ensure that the versions of build tools are up to date by running `pip install --upgrade pip setuptools wheel`. Finally, you can check if any external Windows and Linux dependencies need to build form source are installed on your system.

### incomplete-download

The incomplete-download error in pip (often appearing as an "IncompleteRead" or a hash mismatch) typically occurs when a network interruption leaves a corrupted file in your cache, or when your local environment runs out of disk space.

**What you can do:**

First, check the disk space available for the installation is sufficient. Next, you can purge the cache of the corrupted file by running `pip cache purge` and re-initiating the download. Finally, you can bypass the cache for the single installation using `pip install --no-cache-dir`.

### invalid-egg-fragment

The invalid-egg-fragment error occurs because modern versions of pip (specifically version 25.0 and later) have removed support for complex #egg= fragments in URLs. This fragment was previously used to specify package names and extras in VCS (Version Control System) links, but it has been deprecated in favor of more modern standards.

**What you can do:**

Replace the old fragment-style URL with the PackageName @ URL format:

Old (Broken): `pip install git+https://github.com[extra]`

New (Correct): `pip install "pkgname[extra] @ git+https://github.com"`

If a subdirectory is used, the full format becomes `pip install "pkgname[extra] @ git+https://github.com/user/project.git#subdirectory=path/to/subdir"`

### invalid-installed-package

The "invalid-installed-package" error (often appearing as an InvalidRequirement or InvalidDistribution warning) typically occurs when pip encounters a corrupted or improperly named folder in your Python site-packages directory. This often happens due to failed uninstalls or interrupted upgrades.

**What you can do:**

Clear the pip cache `pip cache purge` and then upgrade pip `pip install --upgrade pip`. Then find the path to the site-packages `python -m site` and look for folders with invalid names such as folders with `~` and delete them.

### invalid-pyproject-build-system-requires

The error invalid-pyproject-build-system-requires occurs when pip encounters a `pyproject.toml` file where the `[build-system]` section has an incorrectly formatted `requires` key.

**What you can do:**

Ensure requires is a list: Check your pyproject.toml and verify that requires is wrapped in brackets. Specify the build-backend such as `build-backend = "setuptools.build_meta"` when applicable.
Incorrect: requires = "setuptools"
Correct: requires = ["setuptools", "wheel"]


### metadata-generation-failed

The `metadata-generation-failed` typically occurs when when pip is unable to generate or read the metadata. This error can happen when the metadata files are corrupted or missing, when the package has an incorrect structure, or a non python dependency is not present.

**What you can do:**

Check that the python version is compatible with the dependencies that you are attempting to install. Ensure the build tools are up to date by running `pip install --upgrade pip setuptools wheel`.

### missing-pyproject-build-system-requires

The error "missing-pyproject-build-system-requires" (or warnings related to it) typically occurs when your pyproject.toml file is missing the mandatory [build-system] table, which pip needs to identify how to build and install your package

**What you can do:**

Add the following block or equivalent to your pyproject.toml file. This tells pip to use setuptools as the default build tool:

```
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"
```

### resolution-too-deep

The `resolution-too-deep` error in pip occurs when its dependency resolver gets stuck in an extremely complex "backtracking" loop. This usually means your set of requirements—or their sub-dependencies—contains so many versions and conflicting constraints that pip cannot find a valid combination within its search limits.

**What you can do:**

If possible, use a fresh virtual environment to avoid contamination from older installations. If possible, specify lower bounds to the versions pip is required to search with the `"package>=2.0.0"` syntax.  If the conflict is caused by a sub-dependency (a "dependency of a dependency"), create a `constraints.txt` file to lock that specific package to a known good version and run `pip install -c constraints.txt -r requirements.txt`. If possible, upgrade the requirements using `pip install --upgrade`. If you are still struggling, explore alternative dependency resolvers.

### subprocess-exited-with-error

The error `subprocess-exited-with-error` is a generic message from pip indicating that a command it tried to run (like a build script or a dependency installer) failed. It usually means the package couldn't be built or installed due to missing tools, incompatible versions, or environment issues.

**What you can do:**

Attempt to diagnose the specific cause by reading the error output. If the output says `ModuleNotFoundError` it is likely the version of python you are using is not compatible with the dependency. If the output says `Permission denied` then it is likely you need admin or sudo access to run the command. If the output says `Failed building wheel` then it is likely pip was unable to find the wheel file for the dependency and attempted to build it from source. Ensure that the versions of build tools are up to date by running `pip install --upgrade pip setuptools wheel`, check that the operating system (OS) contains required external dependencies such as C++ compilers. If the installation requires system dependencies, try to run the installation with `--no-build-isolation` flag to enable interactions between pip and the external system dependency. Finally, this can be avoided if you maintain a pre-compiled wheel for your system and python version which can be installed with the `--pre` flag.

### uninstall-distutils-installed-package

The `uninstall-distutils-installed-package` error happens because pip cannot safely uninstall a package that was installed using the legacy distutils tool. These packages lack a "RECORD" file, which is a modern metadata file that tells pip exactly which files were installed and where they are.

**What you can do:**
Use the `--ignore-installed` flag to tell pip to ignore the installed version and install a new version anyway.

### uninstall-no-record-file

The `uninstall-no-record-file` error occurs when pip tries to remove or upgrade a package but cannot find the metadata file (RECORD) that lists all the files belonging to that installation. This typically happens if the package was installed by a system package manager, or if the installation directory was manually modified or corrupted.

**What you can do:**
Use the `--ignore-installed` flag to tell pip to ignore the installed version and install a new version anyway.
