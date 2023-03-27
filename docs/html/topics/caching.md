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

(wheel-caching)=

### Locally built wheels

pip attempts to use wheels from its local wheel cache whenever possible.

This means that if there is a cached wheel for the same version of a specific
package name, pip will use that wheel instead of rebuilding the project.

When no wheels are found for a source distribution, pip will attempt to build a
wheel using the package's build system. If the build is successful, this wheel
is added to the cache and used in subsequent installs for the same package
version.

Wheels built from source distributions provided to pip as a direct path (such
as `pip install .`) are not cached across runs, though they may be reused within
the same `pip` execution.

```{versionchanged} 20.0
pip now caches wheels when building from an immutable Git reference
(i.e. a commit hash).
```

## Where is the cache stored

```{caution}
The exact filesystem structure of pip's cache's contents is considered to be
an implementation detail and may change between any two versions of pip.
```

### `pip cache dir`

```{versionadded} 20.1

```

You can use `pip cache dir` to get the cache directory that pip is currently configured to use.

### Default paths

````{tab} Linux
```
~/.cache/pip
```

pip will also respect `XDG_CACHE_HOME`.
````

````{tab} MacOS
```
~/Library/Caches/pip
```
````

````{tab} Windows
```
%LocalAppData%\pip\Cache
```
````

## Avoiding caching

pip tries to use its cache whenever possible, and it is designed do the right
thing by default.

In some cases, pip's caching behaviour can be undesirable. As an example, if you
have package with optional C extensions, that generates a pure Python wheel
when the C extension can’t be built, pip will use that cached wheel even when
you later invoke it from an environment that could have built those optional C
extensions. This is because pip is seeing a cached wheel that matches the
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

### General overview

`pip cache info` provides an overview of the contents of pip's cache, such as the total size and location of various parts of it.

### Removing a single package

`pip cache remove setuptools` removes all wheel files related to setuptools from pip's cache.

### Removing the cache

`pip cache purge` will clear all wheel files from pip's cache.

### Listing cached files

`pip cache list` will list all wheel files from pip's cache.

`pip cache list setuptools` will list all setuptools-related wheel files from pip's cache.

## Disabling caching

pip's caching behaviour is disabled by passing the `--no-cache-dir` option.

It is, however, recommended to **NOT** disable pip's caching unless you have caching at a higher level (eg: layered caches in container builds). Doing so can
significantly slow down pip (due to repeated operations and package builds)
and result in significantly more network usage.
