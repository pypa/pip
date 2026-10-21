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

If you need a specific certificate bundle, you can download the
[Mozilla CA bundle provided by the curl project](https://curl.se/docs/caextract.html).

## Using system certificate stores

```{versionadded} 24.2

```

```{versionchanged} 26.3
pip now verifies HTTPS connections using only the system certificate store.
Previously, pip also trusted the certifi bundle that ships with pip.
```

```{note}
Versions of pip prior to v24.2 did not use system certificates by default.
To use system certificates with pip v22.2 or later, you must opt-in using the `--use-feature=truststore` CLI flag.
```

By default, pip uses the system certificate store to verify HTTPS connections.
This functionality is provided through the {pypi}`truststore` package.

If you encounter a TLS/SSL error when using the `truststore` feature you should
open an issue on the [truststore GitHub issue tracker] instead of pip's issue
tracker. The maintainers of truststore will help diagnose and fix the issue.

If your system certificate store is missing certificates that pip previously
accepted via certifi, you can restore the old behavior of trusting both the
system store and certifi by passing `--use-deprecated=legacy-mixed-certs`.

To opt-out of using system certificates entirely you can pass the
`--use-deprecated=legacy-certs` flag to pip. If both flags are given,
`legacy-certs` takes precedence.

[truststore github issue tracker]:
  https://github.com/sethmlarson/truststore/issues
