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

## Structure

Each line of the requirements file indicates something to be installed,
or arguments to {ref}`pip install`. The following forms are supported:

- `[[--option]...]`
- `<requirement specifier> [; markers] [[--option]...]`
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

### Per-requirement options

The options which can be applied to individual requirements are:

- {ref}`--install-option <install_--install-option>`
- {ref}`--global-option <install_--global-option>`
- `--hash` (for {ref}`Hash-Checking mode`)

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

## Example

```
###### Requirements without Version Specifiers ######
pytest
pytest-cov
beautifulsoup4

###### Requirements with Version Specifiers ######
#   See https://www.python.org/dev/peps/pep-0440/#version-specifiers
docopt == 0.6.1             # Version Matching. Must be version 0.6.1
keyring >= 4.1.1            # Minimum version 4.1.1
coverage != 3.5             # Version Exclusion. Anything except version 3.5
Mopidy-Dirble ~= 1.1        # Compatible release. Same as >= 1.1, == 1.*

###### Refer to other requirements files ######
-r other-requirements.txt

###### A particular file ######
./downloads/numpy-1.9.2-cp34-none-win32.whl
http://wxpython.org/Phoenix/snapshot-builds/wxPython_Phoenix-3.0.3.dev1820+49a8884-cp34-none-win_amd64.whl

###### Additional Requirements without Version Specifiers ######
#   Same as 1st section, just here to show that you can put things in any order.
rejected
green
```
