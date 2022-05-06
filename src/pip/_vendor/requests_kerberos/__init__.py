"""
requests Kerberos/GSSAPI authentication library
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Requests is an HTTP library, written in Python, for human beings. This library
adds optional Kerberos/GSSAPI authentication support and supports mutual
authentication. Basic GET usage:

    >>> import requests
    >>> from requests_kerberos import HTTPKerberosAuth
    >>> r = requests.get("http://example.org", auth=HTTPKerberosAuth())

The entire `requests.api` should be supported.
"""
import logging

from .kerberos_ import HTTPKerberosAuth, REQUIRED, OPTIONAL, DISABLED
from .exceptions import MutualAuthenticationError

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = ('HTTPKerberosAuth', 'MutualAuthenticationError', 'REQUIRED',
           'OPTIONAL', 'DISABLED')
__version__ = '0.14.0'
