(requirements-file-format)=

# Requirements File Format

Requirements files serve as a list of items to be installed by pip, when
using {ref}`pip install`. Files that use this format are often called
"pip requirements.txt files", since `requirements.txt` is usually what
these files are named (although, that is not a requirement).

```{note}
The requirements file format is closely tied to a number of internal details of
pip (e.g., pip's command line options). The basic format is relatively stable
and portable but the full syntax, as described here, is only intended for
consumption by pip, and other tools should take that into account before using
it for their own purposes.
```

## Example

```
# This is a comment, to show how #-prefixed lines are ignored.
# It is possible to specify requirements as plain names.
pytest
pytest-cov
beautifulsoup4

# The syntax supported here is the same as that of requirement specifiers.
docopt == 0.6.1
requests [security] >= 2.8.1, == 2.8.* ; python_version < "2.7"
urllib3 @ https://github.com/urllib3/urllib3/archive/refs/tags/1.26.8.zip

# It is possible to refer to other requirement files or constraints files.
-r other-requirements.txt
-c constraints.txt

# It is possible to refer to specific local distribution paths.
./downloads/numpy-1.9.2-cp34-none-win32.whl

# It is possible to refer to URLs.
http://wxpython.org/Phoenix/snapshot-builds/wxPython_Phoenix-3.0.3.dev1820+49a8884-cp34-none-win_amd64.whl
```

## Structure

Each line of the requirements file indicates something to be installed,
or arguments to {ref}`pip install`. The following forms are supported:

- `[[--option]...]`
- `<requirement specifier>`
- `<archive url/path>`
- `[-e] <local project path>`
- `[-e] <vcs project url>`

For details on requirement specifiers, see {ref}`Requirement Specifiers`. For
examples of all these forms, see {ref}`pip install Examples`.

### Encoding

Requirements files are `utf-8` encoding by default and also support
{pep}`263` style comments to change the encoding (i.e.
`# -*- coding: <encoding name> -*-`).

### Line continuations

A line ending in an unescaped `\` is treated as a line continuation
and the newline following it is effectively ignored.

### Comments

A line that begins with `#` is treated as a comment and ignored. Whitespace
followed by a `#` causes the `#` and the remainder of the line to be
treated as a comment.

Comments are stripped _after_ line continuations are processed.

## Supported options

Requirements files only supports certain pip install options, which are listed
below.

### Global options

The following options have an effect on the _entire_ `pip install` run, and
must be specified on their individual lines.

```{eval-rst}
.. pip-requirements-file-options-ref-list::
```

````{admonition} Example
To specify {ref}`--pre <install_--pre>`, {ref}`--no-index <install_--no-index>`
and two {ref}`--find-links <install_--find-links>` locations:

```
--pre
--no-index
--find-links /my/local/archives
--find-links http://some.archives.com/archives
```
````

(per-requirement-options)=

### Per-requirement options

```{versionadded} 7.0

```

The options which can be applied to individual requirements are:

- {ref}`--global-option <install_--global-option>`
- {ref}`--config-settings <install_--config-settings>`
- `--hash` (for {ref}`Hash-checking mode`)

## Referring to other requirements files

If you wish, you can refer to other requirements files, like this:

```
-r more_requirements.txt
```

You can also refer to {ref}`constraints files <Constraints Files>`, like this:

```
-c some_constraints.txt
```

## Using environment variables

```{versionadded} 10.0

```

pip supports the use of environment variables inside the
requirements file.

You have to use the POSIX format for variable names including brackets around
the uppercase name as shown in this example: `${API_TOKEN}`. pip will attempt
to find the corresponding environment variable defined on the host system at
runtime.

```{note}
There is no support for other variable expansion syntaxes such as `$VARIABLE`
and `%VARIABLE%`.
```

You can now store sensitive data (tokens, keys, etc.) in environment variables
and only specify the variable name for your requirements, letting pip lookup
the value at runtime. This approach aligns with the commonly used
[12-factor configuration pattern](https://12factor.net/config).


## Influencing the build system

```{danger}
This disables the use of wheels (cached or otherwise). This could mean that builds will be slower, less deterministic, less reliable and may not behave correctly upon installation.

This mechanism is only preserved for backwards compatibility and should be considered deprecated. A future release of pip may drop these options.
```

The `--global-option` option is used to pass options to `setup.py`.

```{attention}
These options are highly coupled with how pip invokes setuptools using the {doc}`../reference/build-system/setup-py` build system interface. It is not compatible with newer {doc}`../reference/build-system/pyproject-toml` build system interface.

This is will not work with other build-backends or newer setup.cfg-only projects.
```

If you have a declaration like:

    FooProject >= 1.2 --global-option="--no-user-cfg"

The above translates roughly into running FooProject's `setup.py` script as:

    python setup.py --no-user-cfg install

Note that the only way of giving more than one option to `setup.py` is through multiple `--global-option` options.
