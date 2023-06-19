# Authentication

## Basic HTTP authentication

pip supports basic HTTP-based authentication credentials. This is done by
providing the username (and optionally password) in the URL:

```
https://username:password@pypi.company.com/simple
```

For indexes that only require single-part authentication tokens, provide the
token as the "username" and do not provide a password:

```
https://0123456789abcdef@pypi.company.com/simple
```

### Percent-encoding special characters

```{versionadded} 10.0
```

Certain special characters are not valid in the credential part of a URL.
If the user or password part of your login credentials contain any of these
[special characters][reserved-chars], then they must be percent-encoded. As an
example, for a user with username `user` and password `he//o` accessing a
repository at `pypi.company.com/simple`, the URL with credentials would look
like:

```
https://user:he%2F%2Fo@pypi.company.com/simple
```

[reserved-chars]: https://en.wikipedia.org/wiki/Percent-encoding#Percent-encoding_reserved_characters

## netrc support

pip supports loading credentials from a user's `.netrc` file. If no credentials
are part of the URL, pip will attempt to get authentication credentials for the
URL's hostname from the user's `.netrc` file. This behaviour comes from the
underlying use of {pypi}`requests`, which in turn delegates it to the
[Python standard library's `netrc` module][netrc-std-lib].

```{note}
As mentioned in the [standard library documentation for netrc][netrc-std-lib],
only ASCII characters are allowed in `.netrc` files. Whitespace and
non-printable characters are not allowed in passwords.
```

Below is an example `.netrc`, for the host `example.com`, with a user named
`daniel`, using the password `qwerty`:

```
machine example.com
login daniel
password qwerty
```

More information about the `.netrc` file format can be found in the GNU [`ftp`
man pages][netrc-docs].

[netrc-docs]: https://www.gnu.org/software/inetutils/manual/html_node/The-_002enetrc-file.html
[netrc-std-lib]: https://docs.python.org/3/library/netrc.html

## Keyring Support

pip supports loading credentials stored in your keyring using the
{pypi}`keyring` library, which can be enabled py passing `--keyring-provider`
with a value of `auto`, `disabled`, `import`, or `subprocess`. The default
value `auto` respects `--no-input` and not query keyring at all if the option
is used; otherwise it tries the `import`, `subprocess`, and `disabled`
providers (in this order) and uses the first one that works.

### Configuring pip's keyring usage

Since the keyring configuration is likely system-wide, a more common way to
configure its usage would be to use a configuration instead:

```{seealso}
{doc}`./configuration` describes how pip configuration works.
```

```bash
$ pip config set --global global.keyring-provider subprocess

# A different user on the same system which has PYTHONPATH configured and and
# wanting to use keyring installed that way could then run
$ pip config set --user global.keyring-provider import

# For a specific virtual environment you might want to use disable it again
# because you will only be using PyPI and the private repo (and mirror)
# requires 2FA with a keycard and a pincode
$ pip config set --site global.index https://pypi.org/simple
$ pip config set --site global.keyring-provider disabled

# configuring it via environment variable is also possible
$ export PIP_KEYRING_PROVIDER=disabled
```

### Using keyring's Python module

Setting `keyring-provider` to `import` makes pip communicate with `keyring` via
its Python interface.

```bash
# install keyring from PyPI
$ pip install keyring --index-url https://pypi.org/simple
$ echo "your-password" | keyring set pypi.company.com your-username
$ pip install your-package --keyring-provider import --index-url https://pypi.company.com/
```

### Using keyring as a command line application

Setting `keyring-provider` to `subprocess` makes pip look for and use the
`keyring` command found on `PATH`.

For this use case, a username *must* be included in the URL, since it is
required by `keyring`'s command line interface. See the example below or the
basic HTTP authentication section at the top of this page.

```bash
# Install keyring from PyPI using pipx, which we assume is installed properly
# you can also create a venv somewhere and add it to the PATH yourself instead
$ pipx install keyring --index-url https://pypi.org/simple

# For Azure DevOps, also install its keyring backend.
$ pipx inject keyring artifacts-keyring --index-url https://pypi.org/simple

# For Google Artifact Registry, also install and initialize its keyring backend.
$ pipx inject keyring keyrings.google-artifactregistry-auth --index-url https://pypi.org/simple
$ gcloud auth login

# Note that a username is required in the index URL.
$ pip install your-package --keyring-provider subprocess --index-url https://username@pypi.example.com/
```

### Here be dragons

The `auto` provider is conservative and does not query keyring at all when
`--no-input` is used because the keyring might require user interaction such as
prompting the user on the console. Third party tools frequently call Pip for
you and do indeed pass `--no-input` as they are well-behaved and don't have
much information to work with. (Keyring does have an api to request a backend
that does not require user input.) You have more information about your system,
however!

You can force keyring usage by requesting a keyring provider other than `auto`
(or `disabled`). Leaving `import` and `subprocess`. You do this by passing
`--keyring-provider import` or one of the following methods:

```bash
# via config file, possibly with --user, --global or --site
$ pip config set global.keyring-provider subprocess
# or via environment variable
$ export PIP_KEYRING_PROVIDER=import
```

```{warning}
Be careful when doing this since it could cause tools such as pipx and Pipenv
to appear to hang. They show their own progress indicator while hiding output
from the subprocess in which they run Pip. You won't know whether the keyring
backend is waiting the user input or not in such situations.
```

pip is conservative and does not query keyring at all when `--no-input` is used
because the keyring might require user interaction such as prompting the user
on the console. You can force keyring usage by passing `--force-keyring` or one
of the following:

```bash
# possibly with --user, --global or --site
$ pip config set global.force-keyring true
# or
$ export PIP_FORCE_KEYRING=1
```

```{warning}
Be careful when doing this since it could cause tools such as pipx and Pipenv
to appear to hang. They show their own progress indicator while hiding output
from the subprocess in which they run Pip. You won't know whether the keyring
backend is waiting the user input or not in such situations.
```

Note that `keyring` (the Python package) needs to be installed separately from
pip. This can create a bootstrapping issue if you need the credentials stored in
the keyring to download and install keyring.

It is, thus, expected that users that wish to use pip's keyring support have
some mechanism for downloading and installing {pypi}`keyring`.
