"""The wrap_socket() function from Python 3.2, with support for SNI."""

from . import _ssl
from ._ssl import HAS_SNI, CERT_NONE, PROTOCOL_SSLv23
try:
    from ._ssl import PROTOCOL_SSLv2
    _SSLv2_IF_EXISTS = PROTOCOL_SSLv2
except ImportError:
    _SSLv2_IF_EXISTS = None

# Disable weak or insecure ciphers by default
# (OpenSSL's default setting is 'DEFAULT:!aNULL:!eNULL')
_DEFAULT_CIPHERS = 'DEFAULT:!aNULL:!eNULL:!LOW:!EXPORT:!SSLv2'

import ssl
from socket import socket, _delegate_methods, error as socket_error
import errno

__version__ = '3.2a3'

class SSLSocket(ssl.SSLSocket):

    def __init__(self, sock, keyfile=None, certfile=None,
                 server_side=False, cert_reqs=CERT_NONE,
                 ssl_version=PROTOCOL_SSLv23, ca_certs=None,
                 do_handshake_on_connect=True,
                 suppress_ragged_eofs=True, ciphers=None,
                 server_hostname=None):
        socket.__init__(self, _sock=sock._sock)
        # The initializer for socket overrides the methods send(), recv(), etc.
        # in the instancce, which we don't need -- but we want to provide the
        # methods defined in SSLSocket.
        for attr in _delegate_methods:
            try:
                delattr(self, attr)
            except AttributeError:
                pass

        if ciphers is None and ssl_version != _SSLv2_IF_EXISTS:
            ciphers = _DEFAULT_CIPHERS

        if certfile and not keyfile:
            keyfile = certfile

        if server_side and server_hostname:
            raise ValueError("server_hostname can only be specified "
                             "in client mode")

        # see if it's connected
        try:
            socket.getpeername(self)
        except socket_error, e:
            if e.errno != errno.ENOTCONN:
                raise
            # no, no connection yet
            self._connected = False
            self._sslobj = None
        else:
            # yes, create the SSL object
            self._connected = True
            self._sslobj = _ssl.sslwrap(self._sock, server_side,
                                        keyfile, certfile,
                                        cert_reqs, ssl_version, ca_certs,
                                        ciphers, server_hostname)
            if do_handshake_on_connect:
                self.do_handshake()
        self.keyfile = keyfile
        self.certfile = certfile
        self.cert_reqs = cert_reqs
        self.ssl_version = ssl_version
        self.ca_certs = ca_certs
        self.ciphers = ciphers
        self.server_hostname = server_hostname
        self.do_handshake_on_connect = do_handshake_on_connect
        self.suppress_ragged_eofs = suppress_ragged_eofs
        self._makefile_refs = 0

    def _real_connect(self, addr, return_errno):
        # Here we assume that the socket is client-side, and not
        # connected at the time of the call.  We connect it, then wrap it.
        if self._connected:
            raise ValueError("attempt to connect already-connected SSLSocket!")
        self._sslobj = _ssl.sslwrap(self._sock, False, self.keyfile, self.certfile,
                                    self.cert_reqs, self.ssl_version,
                                    self.ca_certs, self.ciphers, self.server_hostname)
        try:
            socket.connect(self, addr)
            if self.do_handshake_on_connect:
                self.do_handshake()
        except socket_error as e:
            if return_errno:
                return e.errno
            else:
                self._sslobj = None
                raise e
        self._connected = True
        return 0

def wrap_socket(sock, keyfile=None, certfile=None,
                server_side=False, cert_reqs=CERT_NONE,
                ssl_version=PROTOCOL_SSLv23, ca_certs=None,
                do_handshake_on_connect=True,
                suppress_ragged_eofs=True, ciphers=None,
                server_hostname=None):

    return SSLSocket(sock, keyfile=keyfile, certfile=certfile,
                     server_side=server_side, cert_reqs=cert_reqs,
                     ssl_version=ssl_version, ca_certs=ca_certs,
                     do_handshake_on_connect=do_handshake_on_connect,
                     suppress_ragged_eofs=suppress_ragged_eofs,
                     ciphers=ciphers, server_hostname=server_hostname)
