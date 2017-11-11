"""
requests Kerberos/GSSAPI authentication library
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Requests is an HTTP library, written in Python, for human beings. This library
adds optional Kerberos/GSSAPI authentication support and supports mutual
authentication. Basic GET usage:

    >>> import pip._vendor.requests
    >>> from pip._vendor.requests_kerberos import HTTPKerberosAuth
    >>> r = pip._vendor.requests.get("http://example.org", auth=HTTPKerberosAuth())

The entire `requests.api` should be supported.
"""
import logging

from .kerberos_ import HTTPKerberosAuth, REQUIRED, OPTIONAL, DISABLED
from .exceptions import MutualAuthenticationError
from .compat import NullHandler

logging.getLogger(__name__).addHandler(NullHandler())

__all__ = ('HTTPKerberosAuth', 'MutualAuthenticationError', 'REQUIRED',
           'OPTIONAL', 'DISABLED')
__version__ = '0.11.0'
