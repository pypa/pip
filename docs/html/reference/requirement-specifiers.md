(Requirement Specifiers)=

# Requirement Specifiers

pip supports installing from a package index using a {term}`requirement specifier <pypug:Requirement Specifier>`. Generally speaking, a requirement specifier is composed of a project name followed by optional {term}`version specifiers <pypug:Version Specifier>`.

{pep}`508` contains a full specification of the format of a requirement.

```{versionadded} 6.0
Support for environment markers.
```

```{versionadded} 19.1
Support for the direct URL reference form.
```

## Overview

A requirement specifier comes in two forms:

- name-based, which is composed of:

  - a package name (eg: `requests`)
  - optionally, a set of "extras" that serve to install optional dependencies (eg: `security`)
  - optionally, constraints to apply on the version of the package
  - optionally, environment markers

- URL-based, which is composed of:

  - a package name (eg: `requests`)
  - optionally, a set of "extras" that serve to install optional dependencies (eg: `security`)
  - a URL for the package
  - optionally, environment markers

## Examples

A few example name-based requirement specifiers:

```
SomeProject
SomeProject == 1.3
SomeProject >= 1.2, < 2.0
SomeProject[foo, bar]
SomeProject ~= 1.4.2
SomeProject == 5.4 ; python_version < '3.8'
SomeProject ; sys_platform == 'win32'
requests [security] >= 2.8.1, == 2.8.* ; python_version < "2.7"
```

```{note}
Use quotes around specifiers in the shell when using `>`, `<`, or when using environment markers.

Do _not_ use quotes in requirement files. There is only one exception: pip v7.0 and v7.0.1 (from May 2015) required quotes around specifiers containing environment markers in requirement files.
```

A few example URL-based requirement specifiers:

```none
pip @ https://github.com/pypa/pip/archive/22.0.2.zip
requests [security] @ https://github.com/psf/requests/archive/refs/heads/main.zip ; python_version >= "3.11"
```
