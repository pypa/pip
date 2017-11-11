"""
requests_kerberos.exceptions
~~~~~~~~~~~~~~~~~~~

This module contains the set of exceptions.

"""
from pip._vendor.requests.exceptions import RequestException


class MutualAuthenticationError(RequestException):
    """Mutual Authentication Error"""

class KerberosExchangeError(RequestException):
    """Kerberos Exchange Failed Error"""
