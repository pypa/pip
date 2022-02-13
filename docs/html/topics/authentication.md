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

When you specify several indexes, each of them can come with its own
authentication information. When the domains and schemes of multiple
indexes partially overlap, you can specify different authentication for each of them
For example you can have:

```
PIP_INDEX_URL=https://build:password1@pkgs.dev.azure.com/feed1
PIP_EXTRA_INDEX_URL=https://build:password2@pkgs.dev.azure.com/feed2
```

If you specify multiple identical index URLs with different authentication information,
authentication from the first index will be used.

```{versionchanged} 22.1
The basic authentication is now compliant with RFC 7617
```

In compliance with [RFC7617](https://datatracker.ietf.org/doc/html/rfc7617#section-2.2) if the indexes
overlap, the authentication information from the prefix-match will be reused for the longer index if
the longer index does not contain the authentication information. In case multiple indexes are
prefix-matching, the authentication of the first of the longest matching prefixes is used.

For example in this case, build:password authentication will be used when authenticating with the extra
index URL.

```
PIP_INDEX_URL=https://build:password@pkgs.dev.azure.com/
PIP_EXTRA_INDEX_URL=https://pkgs.dev.azure.com/feed1
```

```{note}
Prior to version 22.1 reusing of basic authentication between URLs was not RFC7617 compliant.
This could lead to the situation that custom-built indexes could receive the authentication
provided for the index path, to download files outside fof the security domain of the path.

For example if your index at https://username:password@pypi.company.com/simple served files from
https://pypi.company.com/file.tar.gz - the username and password provided for the "/simple" path
was also used to authenticate download of the `file.tar.gz`. This is not RFC7617 compliant and as of
version 22.1 it will not work automatically. If you encounter a problem where your files are being
served from different security domain than your index and authentication is not used for them, you
should (ideally) fix it on your server side or (as temporary workaround)
specify your file download location as extra index url:

PIP_EXTRA_INDEX_URL=https://username:password@pypi.company.com/

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
