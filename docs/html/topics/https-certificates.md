(SSL Certificate Verification)=

# HTTPS Certificates

```{versionadded} 1.3

```

By default, pip will perform SSL certificate verification for network
connections it makes over HTTPS. These serve to prevent man-in-the-middle
attacks against package downloads. Pip by default uses a bundled CA certificate
store from {pypi}`certifi`.

## Using a specific certificate store

The `--cert` option (and the corresponding `PIP_CERT` environment variable)
allow users to specify a different certificate store/bundle for pip to use. It
is also possible to use `REQUESTS_CA_BUNDLE` or `CURL_CA_BUNDLE` environment
variables.

## Using system certificate stores

```{versionadded} 24.2

```

If Python 3.10 or later is being used then by default
system certificates are used in addition to certifi to verify HTTPS connections.
This functionality is provided through the {pypi}`truststore` package.

If you encounter a TLS/SSL error when using the `truststore` feature you should
open an issue on the [truststore GitHub issue tracker] instead of pip's issue
tracker. The maintainers of truststore will help diagnose and fix the issue.

To opt-out of using system certificates you can pass the `--use-deprecated=legacy-certs`
flag to pip.

```{warning}
If Python 3.9 or earlier is in use then only certifi is used to verify HTTPS connections.
```

[truststore github issue tracker]:
  https://github.com/sethmlarson/truststore/issues
