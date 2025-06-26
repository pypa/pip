# Secure installs

By default, pip does not perform any checks to protect against remote tampering and involves running arbitrary code from distributions. It is, however, possible to use pip in a manner that changes these behaviours, to provide a more secure installation mechanism.

This can be achieved by doing the following:

- Enable {ref}`Hash-checking mode`, by passing {any}`--require-hashes`
- Disallow source distributions, by passing {any}`--only-binary :all: <--only-binary>`

(Hash-checking mode)=

## Hash-checking Mode

```{versionadded} 8.0

```

This mode uses local hashes, embedded in a requirements.txt file, to protect against remote tampering and network issues. These hashes are specified using a `--hash` [per requirement option](per-requirement-options).

Note that hash-checking is an all-or-nothing proposition. Specifying `--hash` against _any_ requirement will activate this mode globally.

To add hashes for a package, add them to line as follows:

```
FooProject == 1.2 \
  --hash=sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824 \
  --hash=sha256:486ea46224d1bb4fb680f34f7c9ad96a8f24ec88be73ea8e5a6c65260e9cb8a7
```

### Additional restrictions

- Hashes are required for _all_ requirements.

  This is because a partially-hashed requirements file is of little use and thus likely an error: a malicious actor could slip bad code into the installation via one of the unhashed requirements.

  Note that hashes embedded in URL-style requirements via the `#md5=...` syntax suffice to satisfy this rule (regardless of hash strength, for legacy reasons), though you should use a stronger hash like sha256 whenever possible.

- Hashes are required for _all_ dependencies.

  If there is a dependency that is not spelled out and hashed in the requirements file, it will result in an error.

- Requirements must be pinned (either to a URL, filesystem path or using `==`).

  This prevents a surprising hash mismatch upon the release of a new version that matches the requirement specifier.

### Forcing Hash-checking mode

It is possible to force the hash checking mode to be enabled, by passing `--require-hashes` command-line option.

This can be useful in deploy scripts, to ensure that the author of the requirements file provided hashes. It is also a convenient way to bootstrap your list of hashes, since it shows the hashes of the packages it fetched. It fetches only the preferred archive for each package, so you may still need to add hashes for alternatives archives using {ref}`pip hash`: for instance if there is both a binary and a source distribution.

### Hash algorithms

The recommended hash algorithm at the moment is sha256, but stronger ones are allowed, including all those supported by `hashlib`. However, weaker ones such as md5, sha1, and sha224 are excluded to avoid giving a false sense of security.

### Multiple hashes per package

It is possible to use multiple hashes for each package. This is important when a package offers binary distributions for a variety of platforms or when it is important to allow both binary and source distributions.

### Interaction with caching

```{versionchanged} 23.1
The {ref}`locally-built wheel cache <wheel-caching>` is used in hash-checking mode too.
```

When installing from the cache of locally built wheels in hash-checking mode, pip verifies
the hashes against those of the original source distribution that was used to build the wheel.
These original hashes are obtained from a `origin.json` file stored in each cache entry.

### Using hashes from PyPI (or other index servers)

PyPI (and certain other index servers) provides a hash for the distribution, in the fragment portion of each download URL, like `#sha256=123...`, which pip checks as a protection against download corruption.

Other hash algorithms that have guaranteed support from `hashlib` are also supported here: sha1, sha224, sha384, sha256, and sha512. Since this hash originates remotely, it is not a useful guard against tampering and thus does not satisfy the `--require-hashes` demand that every package have a local hash.

## Repeatable installs

Hash-checking mode also works with {ref}`pip download` and {ref}`pip wheel`. See {doc}`../topics/repeatable-installs` for a comparison of hash-checking mode with other repeatability strategies.

```{warning}
Beware of the `setup_requires` keyword arg in {file}`setup.py`. The (rare) packages that use it will cause those dependencies to be downloaded by setuptools directly, skipping pip's hash-checking. If you need to use such a package, see {ref}`controlling setup_requires <controlling-setup_requires>`.
```

## Do not use setuptools directly

Be careful not to nullify all your security work by installing your actual project by using setuptools' deprecated interfaces directly: for example, by calling `python setup.py install`, `python setup.py develop`, or `easy_install`.

These will happily go out and download, unchecked, anything you missed in your requirements file and it’s easy to miss things as your project evolves. To be safe, install your project using pip and {any}`--no-deps`.

Instead of `python setup.py install`, use:

```{pip-cli}
$ pip install --no-deps .
```

Instead of `python setup.py develop`, use:

```{pip-cli}
$ pip install --no-deps -e .
```
