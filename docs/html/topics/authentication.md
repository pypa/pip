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
{pypi}`keyring` library.

```bash
$ pip install keyring  # install keyring from PyPI
$ echo "your-password" | keyring set pypi.company.com your-username
$ pip install your-package --index-url https://pypi.company.com/
```

Note that `keyring` (the Python package) needs to be installed separately from
pip. This can create a bootstrapping issue if you need the credentials stored in
the keyring to download and install keyring.

It is, thus, expected that users that wish to use pip's keyring support have
some mechanism for downloading and installing {pypi}`keyring` in their Python
environment.
