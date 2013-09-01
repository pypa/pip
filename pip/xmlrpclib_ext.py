###
# Extend xmlrpclib to use http proxy.
# Only http proxy is supported.
# Proxy auth is not supported
###

#coding=utf-8

import xmlrpclib
import urllib2
import httplib
import urlparse

try:
    import gzip
except ImportError:
    #python can be built without zlib/gzip support
    gzip = None 
 
class HttpProxyTransport(xmlrpclib.Transport):

    def __init__(self, proxy, use_datetime=0):

        self._use_datetime = use_datetime
        self._connection = (None, None)
        self._extra_headers = []

        self.proxy = self.proxy_format(proxy)

    def proxy_format(self, proxy):
        if len(proxy.split('://')) < 2:
            proxy = 'http://' + proxy
        url = urlparse.urlparse(proxy)
        if url.scheme != 'http':
            raise Exception(url.scheme.capitalize() + ' proxy is not supported.')
        return url

    def send_request(self, connection, handler, request_body):
        target = 'http://' + self._connection[0] + handler
        if (self.accept_gzip_encoding and gzip):
            connection.putrequest("POST", target, skip_accept_encoding=True)
            connection.putheader("Accept-Encoding", "gzip")
        else:
            connection.putrequest("POST", target)


    def make_connection(self, host):
        #return an existing connection if possible.  This allows
        #HTTP/1.1 keep-alive.
        if self._connection and host == self._connection[0]:
            return self._connection[1]

        # create a HTTP connection object from a host descriptor
        chost, self._extra_headers, x509 = self.get_host_info(host)
        #store the host argument along with the connection object
        self._connection = host, httplib.HTTPConnection(
                host=self.proxy.hostname, 
                port=self.proxy.port
                )
        return self._connection[1]

