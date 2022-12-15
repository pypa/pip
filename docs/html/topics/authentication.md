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
{pypi}`keyring` library which can be enabled py passing `--keyring-provider`
with a value of `auto`, `disabled`, `import` or `subprocess`. The default value
is `auto`. `auto` will respect `--no-input` and not query keyring at all if that
option is used. The `auto` provider will use the `import` provider if the
`keyring` module can be imported. If that is not the case it will use the
`subprocess` provider if a `keyring` executable can be found. Otherwise, the
`disabled` provider will be used.

### Configuring Pip
Passing this as a command line argument will work, but is not how the majority
of this feature's users will use it. They instead will want to overwrite the
default of `disabled` in the global, user of site configuration file:
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

### Installing and using the keyring python module

Setting it to `import` tries to communicate with `keyring` by importing it
and using its Python api.

```bash
# install keyring from PyPI
$ pip install keyring --index-url https://pypi.org/simple
$ echo "your-password" | keyring set pypi.company.com your-username
$ pip install your-package --keyring-provider import --index-url https://pypi.company.com/
```

### Installing and using the keyring cli application

Setting it to `subprocess` will look for a `keyring` executable on the PATH
if one can be found that is different from the `keyring` installation `import`
would be using.

The cli requires a username, therefore you MUST put a username in the url.
See the example below or the basic HTTP authentication section at the top of
this page.

```bash
# install keyring from PyPI using pipx, which we assume if installed properly
# you can also create a venv somewhere and add it to the PATH yourself instead
$ pipx install keyring --index-url https://pypi.org/simple

# install the keyring backend for Azure DevOps for example
# VssSessionToken is the username you MUST use for this backend
$ pipx inject keyring artifacts-keyring --index-url https://pypi.org/simple

# or the one for Google Artifact Registry
$ pipx inject keyring keyrings.google-artifactregistry-auth --index-url https://pypi.org/simple
$ gcloud auth login

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
Be careful when doing this since it could cause tools such as Pipx and Pipenv
to appear to hang. They show their own progress indicator while hiding output
from the subprocess in which they run Pip. You won't know whether the keyring
backend is waiting the user input or not in such situations.
```

Pip is conservative and does not query keyring at all when `--no-input` is used
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
Be careful when doing this since it could cause tools such as Pipx and Pipenv
to appear to hang. They show their own progress indicator while hiding output
from the subprocess in which they run Pip. You won't know whether the keyring
backend is waiting the user input or not in such situations.
```

Note that `keyring` (the Python package) needs to be installed separately from
pip. This can create a bootstrapping issue if you need the credentials stored in
the keyring to download and install keyring.

It is, thus, expected that users that wish to use pip's keyring support have
some mechanism for downloading and installing {pypi}`keyring`.
