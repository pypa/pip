(SSL Certificate Verification)=

# HTTPS Certificates

```{versionadded} 1.3

```

By default, pip will perform SSL certificate verification for network
connections it makes over HTTPS. These serve to prevent man-in-the-middle
attacks against package downloads.

## Using a specific certificate store

The `--cert` option (and the corresponding `PIP_CERT` environment variable)
allow users to specify a different certificate store/bundle for pip to use. It
is also possible to use `REQUESTS_CA_BUNDLE` or `CURL_CA_BUNDLE` environment
variables.

## Using system certificate stores

```{versionadded} 24.2

```

```{note}
Versions of pip prior to v24.2 did not use system certificates by default.
To use system certificates with pip v22.2 or later, you must opt-in using the `--use-feature=truststore` CLI flag.
```

On Python 3.10 or later, by default
system certificates are used in addition to certifi to verify HTTPS connections.
This functionality is provided through the {pypi}`truststore` package.

If you encounter a TLS/SSL error when using the `truststore` feature you should
open an issue on the [truststore GitHub issue tracker] instead of pip's issue
tracker. The maintainers of truststore will help diagnose and fix the issue.

To opt-out of using system certificates you can pass the `--use-deprecated=legacy-certs`
flag to pip.

```{warning}
On Python 3.9 or earlier, only certifi is used to verify HTTPS connections as
`truststore` requires Python 3.10 or higher to function.

The system certificate store won't be used in this case, so some situations like proxies
with their own certificates may not work. Upgrading to at least Python 3.10 or later is
the recommended method to resolve this issue.
```

[truststore github issue tracker]:
  https://github.com/sethmlarson/truststore/issues
