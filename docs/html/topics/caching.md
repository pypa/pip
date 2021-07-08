# Caching

```{versionadded} 6.0
```

pip provides an on-by-default caching, designed to reduce the amount of time
spent on duplicate downloads and builds.

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

This means that if there is a cached wheel for the same version of a specific
package name, pip will use that wheel instead of rebuilding the project.

When no wheels are found for a source distribution, pip will attempt to build a
wheel using the package's build system. If the build is successful, this wheel
is added to the cache and used in subsequent installs for the same package
version.

```{versionchanged} 20.0
pip now caches wheels when building from an immutable Git reference
(i.e. a commit hash).
```

## Avoiding caching

pip tries to use its cache whenever possible, and it is designed do the right
thing by default.

In some cases, pip's caching behaviour can be undesirable. As an example, if you
have package with optional C extensions, that generates a pure Python wheel
when the C extension can’t be built, pip will use that cached wheel even when
you later invoke it from an environment that could have built those optional C
extensions. This is because pip is seeing a cached wheel for that matches the
package being built, and pip assumes that the result of building a package from
a package index is deterministic.

The recommended approach for dealing with these situations is to directly
install from a source distribution instead of letting pip auto-discover the
package when it is trying to install. Installing directly from a source
distribution will make pip build a wheel, regardless of whether there is a
matching cached wheel. This usually means doing something like:

```{pip-cli}
$ pip download sampleproject==1.0.0 --no-binary :all:
$ pip install sampleproject-1.0.0.tar.gz
```

It is also a good idea to remove the offending cached wheel using the
{ref}`pip cache` command.

## Cache management

The {ref}`pip cache` command can be used to manage pip's cache.

The exact filesystem structure of pip's cache is considered to be an
implementation detail and may change between any two versions of pip.

## Disabling caching

pip's caching behaviour is disabled by passing the ``--no-cache-dir`` option.

It is, however, recommended to **NOT** disable pip's caching. Doing so can
significantly slow down pip (due to repeated operations and package builds)
and result in significantly more network usage.
