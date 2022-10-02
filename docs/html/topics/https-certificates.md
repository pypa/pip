(SSL Certificate Verification)=

# HTTPS Certificates

```{versionadded} 1.3

```

By default, pip will perform SSL certificate verification for network
connections it makes over HTTPS. These serve to prevent man-in-the-middle
attacks against package downloads. This does not use the system certificate
store but, instead, uses a bundled CA certificate store from {pypi}`certifi`.

## Using a specific certificate store

The `--cert` option (and the corresponding `PIP_CERT` environment variable)
allow users to specify a different certificate store/bundle for pip to use. It
is also possible to use `REQUESTS_CA_BUNDLE` or `CURL_CA_BUNDLE` environment
variables.

## Using system certificate stores

```{versionadded} 22.2
Experimental support, behind `--use-feature=truststore`.
```

It is possible to use the system trust store, instead of the bundled certifi
certificates for verifying HTTPS certificates. This approach will typically
support corporate proxy certificates without additional configuration.

In order to use system trust stores, you need to:

- Use Python 3.10 or newer.
- Install the {pypi}`truststore` package, in the Python environment you're
  running pip in.

  This is typically done by installing this package using a system package
  manager or by using pip in {ref}`Hash-checking mode` for this package and
  trusting the network using the `--trusted-host` flag.

  ```{pip-cli}
  $ python -m pip install truststore
  [...]
  $ python -m pip install SomePackage --use-feature=truststore
  [...]
  Successfully installed SomePackage
  ```

### When to use

You should try using system trust stores when there is a custom certificate
chain configured for your system that pip isn't aware of. Typically, this
situation will manifest with an `SSLCertVerificationError` with the message
"certificate verify failed: unable to get local issuer certificate":

```{pip-cli}
$ pip install -U SomePackage
[...]
   SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (\_ssl.c:997)'))) - skipping
```

This error means that OpenSSL wasn't able to find a trust anchor to verify the
chain against. Using system trust stores instead of certifi will likely solve
this issue.

If you encounter a TLS/SSL error when using the `truststore` feature you should
open an issue on the [truststore GitHub issue tracker] instead of pip's issue
tracker. The maintainers of truststore will help diagnose and fix the issue.

[truststore github issue tracker]:
  https://github.com/sethmlarson/truststore/issues
