# Configuration

pip allows a user to change its behaviour via 3 mechanisms:

- command line options
- environment variables
- configuration files

This page explains how the configuration files and environment variables work,
and how they are related to pip's various command line options.

## Configuration Files

Configuration files can change the default values for command line option.
They are written using a standard INI style configuration files.

pip has 3 "levels" of configuration files:

- `global`: system-wide configuration file, shared across users.
- `user`: per-user configuration file.
- `site`: per-environment configuration file; i.e. per-virtualenv.

### Location

pip's configuration files are located in fairly standard locations. This
location is different on different operating systems, and has some additional
complexity for backwards compatibility reasons.

```{tab} Unix

Global
: {file}`/etc/pip.conf`

  Alternatively, it may be in a "pip" subdirectory of any of the paths set
  in the environment variable `XDG_CONFIG_DIRS` (if it exists), for
  example {file}`/etc/xdg/pip/pip.conf`.

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
a configuration file that's loaded first, and whose values are overridden by
the values set in the aforementioned files. Setting this to {any}`os.devnull`
disables the loading of _all_ configuration files.

### Loading order

When multiple configuration files are found, pip combines them in the following
order:

- `PIP_CONFIG_FILE`, if given.
- Global
- User
- Site

Each file read overrides any values read from previous files, so if the
global timeout is specified in both the global file and the per-user file
then the latter value will be used.

### Naming

The names of the settings are derived from the long command line option.

As an example, if you want to use a different package index (`--index-url`) and
set the HTTP timeout (`--default-timeout`) to 60 seconds, your config file would
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

## Environment Variables

pip's command line options can be set with environment variables using the
format `PIP_<UPPER_LONG_NAME>` . Dashes (`-`) have to be replaced with
underscores (`_`).

- `PIP_DEFAULT_TIMEOUT=60` is the same as `--default-timeout=60`
- ```
  PIP_FIND_LINKS="http://mirror1.example.com http://mirror2.example.com"
  ```

  is the same as

  ```
  --find-links=http://mirror1.example.com --find-links=http://mirror2.example.com
  ```

Repeatable options that do not take a value (such as `--verbose`) can be
specified using the number of repetitions:

- `PIP_VERBOSE=3` is the same as `pip install -vvv`

```{note}
Environment variables set to an empty string (like with `export X=` on Unix) will **not** be treated as false.
Use `no`, `false` or `0` instead.
```

## Precedence / Override order

Command line options have override environment variables, which override the
values in a configuration file. Within the configuration file, values in
command-specific sections over values in the global section.

Examples:

- `--host=foo` overrides `PIP_HOST=foo`
- `PIP_HOST=foo` overrides a config file with `[global] host = foo`
- A command specific section in the config file `[<command>] host = bar`
  overrides the option with same name in the `[global]` config file section.
