(configuration)=

# Configuration

pip allows a user to change its behaviour via 3 mechanisms.
These mechanisms are listed in order of priority, highest to lowest:

1. command line options
2. [environment variables](env-variables)
3. [configuration files](config-file)

This page explains how the configuration files and environment variables work,
and how they are related to pip's various command line options.

```{seealso}
{doc}`../cli/pip_config` command, which helps manage pip's configuration.
```

(config-file)=

## Configuration Files

Configuration files can change the default values for command line options.
The files are written using standard INI format.

pip has 3 "levels" of configuration files, in order of priority, highest to lowest:

- `site`: per-environment configuration file; i.e. per-virtualenv.
- `user`: per-user configuration file.
- `global`: system-wide configuration file, shared across users.

```{important}
Values in command-specific sections override values in the global section.

Options specified through environment variables or command line options
take precedence over configuration files.
```

### Location

pip's configuration files are located in fairly standard locations. This
location is different on different operating systems, and has some additional
complexity for backwards compatibility reasons. Note that if user config files
exist in both the legacy and current locations, values in the current file
will override values in the legacy file.

```{tab} Unix

Global
: In a "pip" subdirectory of any of the paths set in the environment variable
  `XDG_CONFIG_DIRS` (if it exists), for example {file}`/etc/xdg/pip/pip.conf`.

  This will be followed by loading {file}`/etc/pip.conf`.

User
: {file}`$HOME/.config/pip/pip.conf`, which respects the `XDG_CONFIG_HOME` environment variable.

  The legacy "per-user" configuration file is also loaded, if it exists: {file}`$HOME/.pip/pip.conf`.

Site
: {file}`$VIRTUAL_ENV/pip.conf`
```

```{tab} MacOS

Global
: {file}`/Library/Application Support/pip/pip.conf`

User
: {file}`$HOME/Library/Application Support/pip/pip.conf`
  if directory `$HOME/Library/Application Support/pip` exists
  else {file}`$HOME/.config/pip/pip.conf`

  The legacy "per-user" configuration file is also loaded, if it exists: {file}`$HOME/.pip/pip.conf`.

Site
: {file}`$VIRTUAL_ENV/pip.conf`
```

```{tab} Windows

Global
: * On Windows 7 and later: {file}`C:\\ProgramData\\pip\\pip.ini`
    (hidden but writeable)
  * On Windows Vista: Global configuration is not supported.
  * On Windows XP:
    {file}`C:\\Documents and Settings\\All Users\\Application Data\\pip\\pip.ini`

User
: {file}`%APPDATA%\\pip\\pip.ini`

  The legacy "per-user" configuration file is also loaded, if it exists: {file}`%HOME%\\pip\\pip.ini`

Site
: {file}`%VIRTUAL_ENV%\\pip.ini`
```

### `PIP_CONFIG_FILE`

Additionally, the environment variable `PIP_CONFIG_FILE` can be used to specify
a configuration file that's loaded last, and whose values override the values
set in the aforementioned files. Setting this to {any}`os.devnull`
disables the loading of _all_ configuration files. Note that if a file exists
at the location that this is set to, the user config file will not be loaded.

(config-precedence)=

### Loading order

When multiple configuration files are found, pip combines them in the following
order:

- Global
- User
- Site
- `PIP_CONFIG_FILE`, if given.

Each file read overrides any values read from previous files, so if the
global timeout is specified in both the global file and the per-user file
then the latter value will be used.

### Naming

The names of the settings are derived from the long command line option.

As an example, if you want to use a different package index (`--index-url`) and
set the HTTP timeout (`--timeout`) to 60 seconds, your config file would
look like this:

```ini
[global]
timeout = 60
index-url = https://download.zope.org/ppix
```

### Per-command section

Each subcommand can be configured optionally in its own section. This overrides
the global setting with the same name.

As an example, if you want to decrease the `timeout` to `10` seconds when
running the {ref}`pip freeze`, and use `60` seconds for all other commands:

```ini
[global]
timeout = 60

[freeze]
timeout = 10
```

### Boolean options

Boolean options like `--ignore-installed` or `--no-dependencies` can be set
like this:

```ini
[install]
ignore-installed = true
no-dependencies = yes
```

To enable the boolean options `--no-compile`, `--no-warn-script-location` and
`--no-cache-dir`, falsy values have to be used:

```ini
[global]
no-cache-dir = false

[install]
no-compile = no
no-warn-script-location = false
```

### Repeatable options

For options which can be repeated like `--verbose` and `--quiet`, a
non-negative integer can be used to represent the level to be specified:

```ini
[global]
quiet = 0
verbose = 2
```

It is possible to append values to a section within a configuration file. This
is applicable to appending options like `--find-links` or `--trusted-host`,
which can be written on multiple lines:

```ini
[global]
find-links =
    http://download.example.com

[install]
find-links =
    http://mirror1.example.com
    http://mirror2.example.com

trusted-host =
    mirror1.example.com
    mirror2.example.com
```

This enables users to add additional values in the order of entry for such
command line arguments.

(env-variables)=

## Environment Variables

All pip command line options have equivalent environment variables,
they can be specified using:
```shell
PIP_<UPPERCASE_LONG_NAME>
```

Dashes (`-`) have to be replaced with underscores (`_`).

Examples:

```shell
PIP_VERBOSE=3 PIP_CACHE_DIR=/home/user/tmp pip ...
PIP_FIND_LINKS="http://mirror1.example.com http://mirror2.example.com" pip ...
PIP_NO_DEPS=yes pip ...
# are equivalent to
pip ... -vvv --cache-dir=/home/user/tmp
pip ... --find-links=http://mirror1.example.com --find-links=http://mirror2.example.com
pip ... --no-deps
```

All option values follows the same rules as for the [configuration files](config-file).

```{note}
Environment variables set to an empty string (like with `export X=` on Unix) will **not** be treated as false.
Use `no`, `false` or `0` instead.

Consequently, boolean options prefixed with `--no-*` can be disabled by using
truthy values, e.g. `PIP_NO_CACHE_DIR=true`.
```

```{warning}
`PIP_NO_BUILD_ISOLATION` functions **opposite** to how it reads. For example, to
disable build isolation, `PIP_NO_BUILD_ISOLATION` must be set to a **falsy** value,
e.g. `PIP_NO_BUILD_ISOLATION=off`.

This confusing behavior is known and will be addressed, please see issue {issue}`5735` for
discussion on potential fixes.
```
