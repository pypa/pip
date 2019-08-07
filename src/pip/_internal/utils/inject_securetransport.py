"""A helper module that injects SecureTransport, on import.

The import should be done as early as possible, to ensure all requests and
sessions (or whatever) are created after injecting SecureTransport.

Note that we only do the injection on macOS, when the linked OpenSSL is too
old to handle TLSv1.2.
"""

try:
    import ssl
except ImportError:
    pass
else:
    import sys

    # Checks for OpenSSL 1.0.1 on MacOS
    if sys.platform == "darwin" and ssl.OPENSSL_VERSION_NUMBER < 0x1000100f:
        try:
            from pip._vendor.urllib3.contrib import securetransport
        except (ImportError, OSError):
            pass
        else:
            securetransport.inject_into_urllib3()
