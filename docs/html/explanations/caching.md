# Caching

pip provides an on-by-default caching, designed to reduce the amount of time
spent on duplicate downloads and builds. pip's caching behaviour is disabled
via the ``--no-cache-dir`` option.

## What is cached

### HTTP responses

This cache functions like a web browser cache.

When making any HTTP request, pip will first check its local cache to determine
if it has a suitable response stored for that request which has not expired. If
it does then it returns that response and doesn't re-download the content.

If it has a response stored but it has expired, then it will attempt to make a
conditional request to refresh the cache which will either return an empty
response telling pip to simply use the cached item (and refresh the expiration
timer) or it will return a whole new response which pip can then store in the
cache.

While this cache attempts to minimize network activity, it does not prevent
network access altogether. If you want a local install solution that
circumvents accessing PyPI, see {ref}`Installing from local packages`.

### Locally built wheels

pip attempts to use wheels from its local wheel cache whenever possible.

pip attempts to choose the best wheels from those built in preference to
building a new wheel. Note that this means when a package has both optional
C extensions and builds ``py`` tagged wheels when the C extension can't be built
that pip will not attempt to build a better wheel for Pythons that would have
supported it, once any generic wheel is built. To correct this, make sure that
the wheels are built with Python specific tags - e.g. pp on PyPy.

When no wheels are found for an sdist, pip will attempt to build a wheel
using the package's build system. If the build is successful, this wheel is
added to the cache and used in subsequent installs for the same package version.

```{note}
The structure of pip's wheel cache is not considered public API and may change
between any two versions of pip.
```

```{versionchanged} 7.0
pip now makes a subdirectory for each sdist that wheels are built
from and places the resulting wheels inside.
```

```{versionchanged} 20.0
pip now caches wheels when building from an immutable Git reference
(i.e. a commit hash).
```

## Cache management

pip provides a {ref}`pip cache` command to aid with managing pip's cache.

[TODO: Expand this section with descriptions of how to use pip cache]
