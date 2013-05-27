
import sys
import os
import ssl
from mock import Mock, patch
from pip.download import urlopen, VerifiedHTTPSHandler
from tests.lib import assert_raises_regexp, tests_data, reset_env, run_pip
from nose import SkipTest
from nose.tools import assert_raises
from pip.backwardcompat import urllib2, URLError
from pip.backwardcompat import CertificateError
from pip.exceptions import PipError

pypi_https = 'https://pypi.python.org/simple/'
pypi_http = 'http://pypi.python.org/simple/'

class TestsSSL:
    """ssl tests"""

    def setup(self):
        pass

    def teardown(self):
        os.environ['PIP_CERT'] = ''


    def test_https_ok(self):
        """
        Test https pypi access with pip urlopener
        """
        response = urlopen.get_opener(scheme='https').open(pypi_https)
        assert response.getcode() == 200, str(dir(response))

    def test_http_ok(self):
        """
        Test http pypi access with pip urlopener
        """
        response = urlopen.get_opener().open(pypi_http)
        assert response.getcode() == 200, str(dir(response))

    def test_https_opener_director_handlers(self):
        """
        Confirm the expected handlers in our https OpenerDirector instance
        We're specifically testing it does *not* contain the default http handler
        """
        o = urlopen.get_opener(scheme='https')
        handler_types = [h.__class__ for h in o.handlers]

        assert handler_types == [
            urllib2.UnknownHandler,
            urllib2.HTTPDefaultErrorHandler,
            urllib2.HTTPRedirectHandler,
            urllib2.FTPHandler,
            urllib2.FileHandler,
            VerifiedHTTPSHandler,  #our cert check handler
            urllib2.HTTPErrorProcessor
            ], str(handler_types)

    @patch('ssl.SSLSocket.getpeercert')
    def test_fails_with_no_cert_returning(self, mock_getpeercert):
        """
        Test get ValueError if pypi returns no cert.
        """
        mock_getpeercert.return_value = None
        o = urlopen.get_opener(scheme='https')
        assert_raises_regexp(ValueError, 'empty or no certificate', o.open, pypi_https)


    @patch('pip.download.match_hostname')
    def test_raises_certificate_error(self, mock_match_hostname):
        """
        Test CertificateError gets raised, which implicity confirms the sock.shutdown/sock.close calls ran
        TODO: mock socket._socket.close (to explicitly confirm the close upon exception)
        """
        def mock_matchhostname(cert, host):
            raise CertificateError()

        mock_match_hostname.side_effect = mock_matchhostname
        opener = urlopen.get_opener(scheme='https')
        assert_raises(CertificateError, opener.open, pypi_https)


    def test_bad_pem_fails(self):
        """
        Test ssl verification fails with bad pem file.
        Also confirms alternate --cert-path option works
        """
        bad_cert = os.path.join(tests_data, 'packages', 'README.txt')
        os.environ['PIP_CERT'] = bad_cert
        o = urlopen.get_opener(scheme='https')
        assert_raises_regexp(URLError, '[sS][sS][lL]', o.open, pypi_https)

