from __future__ import absolute_import

import cgi
import email.utils
import json
import logging
import mimetypes
import os
import platform
import re
import shutil
import sys

from pip._vendor import requests, six, urllib3
from pip._vendor.cachecontrol import CacheControlAdapter
from pip._vendor.requests.adapters import BaseAdapter, HTTPAdapter
from pip._vendor.requests.models import CONTENT_CHUNK_SIZE, Response
from pip._vendor.requests.structures import CaseInsensitiveDict
from pip._vendor.six import PY2
# NOTE: XMLRPC Client is not annotated in typeshed as on 2017-07-17, which is
#       why we ignore the type on this import
from pip._vendor.six.moves import xmlrpc_client  # type: ignore
from pip._vendor.six.moves.urllib import parse as urllib_parse

import pip
from pip._internal.exceptions import HashMismatch, InstallationError
from pip._internal.models.index import PyPI
from pip._internal.network.auth import MultiDomainBasicAuth
from pip._internal.network.cache import SafeFileCache
# Import ssl from compat so the initial import occurs in only one place.
from pip._internal.utils.compat import HAS_TLS, ipaddress, ssl
from pip._internal.utils.encoding import auto_decode
from pip._internal.utils.filesystem import check_path_owner, copy2_fixed
from pip._internal.utils.glibc import libc_ver
from pip._internal.utils.misc import (
    ask_path_exists,
    backup_dir,
    build_url_from_netloc,
    consume,
    display_path,
    format_size,
    get_installed_version,
    hide_url,
    parse_netloc,
    path_to_display,
    path_to_url,
    rmtree,
    splitext,
)
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.typing import MYPY_CHECK_RUNNING
from pip._internal.utils.ui import DownloadProgressProvider
from pip._internal.utils.unpacking import unpack_file
from pip._internal.utils.urls import get_url_scheme, url_to_path
from pip._internal.vcs import vcs

if MYPY_CHECK_RUNNING:
    from typing import (
        IO, Callable, Iterator, List, Optional, Text, Tuple, Union,
    )

    from mypy_extensions import TypedDict

    from pip._internal.models.link import Link
    from pip._internal.utils.hashes import Hashes
    from pip._internal.vcs.versioncontrol import VersionControl

    SecureOrigin = Tuple[str, str, Optional[Union[int, str]]]

    if PY2:
        CopytreeKwargs = TypedDict(
            'CopytreeKwargs',
            {
                'ignore': Callable[[str, List[str]], List[str]],
                'symlinks': bool,
            },
            total=False,
        )
    else:
        CopytreeKwargs = TypedDict(
            'CopytreeKwargs',
            {
                'copy_function': Callable[[str, str], None],
                'ignore': Callable[[str, List[str]], List[str]],
                'ignore_dangling_symlinks': bool,
                'symlinks': bool,
            },
            total=False,
        )


__all__ = ['get_file_content',
           'path_to_url',
           'unpack_vcs_link',
           'unpack_file_url', 'is_file_url',
           'unpack_http_url', 'unpack_url',
           'parse_content_disposition', 'sanitize_content_filename']


logger = logging.getLogger(__name__)


SECURE_ORIGINS = [
    # protocol, hostname, port
    # Taken from Chrome's list of secure origins (See: http://bit.ly/1qrySKC)
    ("https", "*", "*"),
    ("*", "localhost", "*"),
    ("*", "127.0.0.0/8", "*"),
    ("*", "::1/128", "*"),
    ("file", "*", None),
    # ssh is always secure.
    ("ssh", "*", "*"),
]  # type: List[SecureOrigin]


# These are environment variables present when running under various
# CI systems.  For each variable, some CI systems that use the variable
# are indicated.  The collection was chosen so that for each of a number
# of popular systems, at least one of the environment variables is used.
# This list is used to provide some indication of and lower bound for
# CI traffic to PyPI.  Thus, it is okay if the list is not comprehensive.
# For more background, see: https://github.com/pypa/pip/issues/5499
CI_ENVIRONMENT_VARIABLES = (
    # Azure Pipelines
    'BUILD_BUILDID',
    # Jenkins
    'BUILD_ID',
    # AppVeyor, CircleCI, Codeship, Gitlab CI, Shippable, Travis CI
    'CI',
    # Explicit environment variable.
    'PIP_IS_CI',
)


def looks_like_ci():
    # type: () -> bool
    """
    Return whether it looks like pip is running under CI.
    """
    # We don't use the method of checking for a tty (e.g. using isatty())
    # because some CI systems mimic a tty (e.g. Travis CI).  Thus that
    # method doesn't provide definitive information in either direction.
    return any(name in os.environ for name in CI_ENVIRONMENT_VARIABLES)


def user_agent():
    """
    Return a string representing the user agent.
    """
    data = {
        "installer": {"name": "pip", "version": pip.__version__},
        "python": platform.python_version(),
        "implementation": {
            "name": platform.python_implementation(),
        },
    }

    if data["implementation"]["name"] == 'CPython':
        data["implementation"]["version"] = platform.python_version()
    elif data["implementation"]["name"] == 'PyPy':
        if sys.pypy_version_info.releaselevel == 'final':
            pypy_version_info = sys.pypy_version_info[:3]
        else:
            pypy_version_info = sys.pypy_version_info
        data["implementation"]["version"] = ".".join(
            [str(x) for x in pypy_version_info]
        )
    elif data["implementation"]["name"] == 'Jython':
        # Complete Guess
        data["implementation"]["version"] = platform.python_version()
    elif data["implementation"]["name"] == 'IronPython':
        # Complete Guess
        data["implementation"]["version"] = platform.python_version()

    if sys.platform.startswith("linux"):
        from pip._vendor import distro
        distro_infos = dict(filter(
            lambda x: x[1],
            zip(["name", "version", "id"], distro.linux_distribution()),
        ))
        libc = dict(filter(
            lambda x: x[1],
            zip(["lib", "version"], libc_ver()),
        ))
        if libc:
            distro_infos["libc"] = libc
        if distro_infos:
            data["distro"] = distro_infos

    if sys.platform.startswith("darwin") and platform.mac_ver()[0]:
        data["distro"] = {"name": "macOS", "version": platform.mac_ver()[0]}

    if platform.system():
        data.setdefault("system", {})["name"] = platform.system()

    if platform.release():
        data.setdefault("system", {})["release"] = platform.release()

    if platform.machine():
        data["cpu"] = platform.machine()

    if HAS_TLS:
        data["openssl_version"] = ssl.OPENSSL_VERSION

    setuptools_version = get_installed_version("setuptools")
    if setuptools_version is not None:
        data["setuptools_version"] = setuptools_version

    # Use None rather than False so as not to give the impression that
    # pip knows it is not being run under CI.  Rather, it is a null or
    # inconclusive result.  Also, we include some value rather than no
    # value to make it easier to know that the check has been run.
    data["ci"] = True if looks_like_ci() else None

    user_data = os.environ.get("PIP_USER_AGENT_USER_DATA")
    if user_data is not None:
        data["user_data"] = user_data

    return "{data[installer][name]}/{data[installer][version]} {json}".format(
        data=data,
        json=json.dumps(data, separators=(",", ":"), sort_keys=True),
    )


class LocalFSAdapter(BaseAdapter):

    def send(self, request, stream=None, timeout=None, verify=None, cert=None,
             proxies=None):
        pathname = url_to_path(request.url)

        resp = Response()
        resp.status_code = 200
        resp.url = request.url

        try:
            stats = os.stat(pathname)
        except OSError as exc:
            resp.status_code = 404
            resp.raw = exc
        else:
            modified = email.utils.formatdate(stats.st_mtime, usegmt=True)
            content_type = mimetypes.guess_type(pathname)[0] or "text/plain"
            resp.headers = CaseInsensitiveDict({
                "Content-Type": content_type,
                "Content-Length": stats.st_size,
                "Last-Modified": modified,
            })

            resp.raw = open(pathname, "rb")
            resp.close = resp.raw.close

        return resp

    def close(self):
        pass


class InsecureHTTPAdapter(HTTPAdapter):

    def cert_verify(self, conn, url, verify, cert):
        conn.cert_reqs = 'CERT_NONE'
        conn.ca_certs = None


class PipSession(requests.Session):

    timeout = None  # type: Optional[int]

    def __init__(self, *args, **kwargs):
        """
        :param trusted_hosts: Domains not to emit warnings for when not using
            HTTPS.
        """
        retries = kwargs.pop("retries", 0)
        cache = kwargs.pop("cache", None)
        trusted_hosts = kwargs.pop("trusted_hosts", [])  # type: List[str]
        index_urls = kwargs.pop("index_urls", None)

        super(PipSession, self).__init__(*args, **kwargs)

        # Namespace the attribute with "pip_" just in case to prevent
        # possible conflicts with the base class.
        self.pip_trusted_origins = []  # type: List[Tuple[str, Optional[int]]]

        # Attach our User Agent to the request
        self.headers["User-Agent"] = user_agent()

        # Attach our Authentication handler to the session
        self.auth = MultiDomainBasicAuth(index_urls=index_urls)

        # Create our urllib3.Retry instance which will allow us to customize
        # how we handle retries.
        retries = urllib3.Retry(
            # Set the total number of retries that a particular request can
            # have.
            total=retries,

            # A 503 error from PyPI typically means that the Fastly -> Origin
            # connection got interrupted in some way. A 503 error in general
            # is typically considered a transient error so we'll go ahead and
            # retry it.
            # A 500 may indicate transient error in Amazon S3
            # A 520 or 527 - may indicate transient error in CloudFlare
            status_forcelist=[500, 503, 520, 527],

            # Add a small amount of back off between failed requests in
            # order to prevent hammering the service.
            backoff_factor=0.25,
        )

        # Check to ensure that the directory containing our cache directory
        # is owned by the user current executing pip. If it does not exist
        # we will check the parent directory until we find one that does exist.
        if cache and not check_path_owner(cache):
            logger.warning(
                "The directory '%s' or its parent directory is not owned by "
                "the current user and the cache has been disabled. Please "
                "check the permissions and owner of that directory. If "
                "executing pip with sudo, you may want sudo's -H flag.",
                cache,
            )
            cache = None

        # We want to _only_ cache responses on securely fetched origins. We do
        # this because we can't validate the response of an insecurely fetched
        # origin, and we don't want someone to be able to poison the cache and
        # require manual eviction from the cache to fix it.
        if cache:
            secure_adapter = CacheControlAdapter(
                cache=SafeFileCache(cache),
                max_retries=retries,
            )
        else:
            secure_adapter = HTTPAdapter(max_retries=retries)

        # Our Insecure HTTPAdapter disables HTTPS validation. It does not
        # support caching (see above) so we'll use it for all http:// URLs as
        # well as any https:// host that we've marked as ignoring TLS errors
        # for.
        insecure_adapter = InsecureHTTPAdapter(max_retries=retries)
        # Save this for later use in add_insecure_host().
        self._insecure_adapter = insecure_adapter

        self.mount("https://", secure_adapter)
        self.mount("http://", insecure_adapter)

        # Enable file:// urls
        self.mount("file://", LocalFSAdapter())

        for host in trusted_hosts:
            self.add_trusted_host(host, suppress_logging=True)

    def add_trusted_host(self, host, source=None, suppress_logging=False):
        # type: (str, Optional[str], bool) -> None
        """
        :param host: It is okay to provide a host that has previously been
            added.
        :param source: An optional source string, for logging where the host
            string came from.
        """
        if not suppress_logging:
            msg = 'adding trusted host: {!r}'.format(host)
            if source is not None:
                msg += ' (from {})'.format(source)
            logger.info(msg)

        host_port = parse_netloc(host)
        if host_port not in self.pip_trusted_origins:
            self.pip_trusted_origins.append(host_port)

        self.mount(build_url_from_netloc(host) + '/', self._insecure_adapter)
        if not host_port[1]:
            # Mount wildcard ports for the same host.
            self.mount(
                build_url_from_netloc(host) + ':',
                self._insecure_adapter
            )

    def iter_secure_origins(self):
        # type: () -> Iterator[SecureOrigin]
        for secure_origin in SECURE_ORIGINS:
            yield secure_origin
        for host, port in self.pip_trusted_origins:
            yield ('*', host, '*' if port is None else port)

    def is_secure_origin(self, location):
        # type: (Link) -> bool
        # Determine if this url used a secure transport mechanism
        parsed = urllib_parse.urlparse(str(location))
        origin_protocol, origin_host, origin_port = (
            parsed.scheme, parsed.hostname, parsed.port,
        )

        # The protocol to use to see if the protocol matches.
        # Don't count the repository type as part of the protocol: in
        # cases such as "git+ssh", only use "ssh". (I.e., Only verify against
        # the last scheme.)
        origin_protocol = origin_protocol.rsplit('+', 1)[-1]

        # Determine if our origin is a secure origin by looking through our
        # hardcoded list of secure origins, as well as any additional ones
        # configured on this PackageFinder instance.
        for secure_origin in self.iter_secure_origins():
            secure_protocol, secure_host, secure_port = secure_origin
            if origin_protocol != secure_protocol and secure_protocol != "*":
                continue

            try:
                # We need to do this decode dance to ensure that we have a
                # unicode object, even on Python 2.x.
                addr = ipaddress.ip_address(
                    origin_host
                    if (
                        isinstance(origin_host, six.text_type) or
                        origin_host is None
                    )
                    else origin_host.decode("utf8")
                )
                network = ipaddress.ip_network(
                    secure_host
                    if isinstance(secure_host, six.text_type)
                    # setting secure_host to proper Union[bytes, str]
                    # creates problems in other places
                    else secure_host.decode("utf8")  # type: ignore
                )
            except ValueError:
                # We don't have both a valid address or a valid network, so
                # we'll check this origin against hostnames.
                if (origin_host and
                        origin_host.lower() != secure_host.lower() and
                        secure_host != "*"):
                    continue
            else:
                # We have a valid address and network, so see if the address
                # is contained within the network.
                if addr not in network:
                    continue

            # Check to see if the port matches.
            if (origin_port != secure_port and
                    secure_port != "*" and
                    secure_port is not None):
                continue

            # If we've gotten here, then this origin matches the current
            # secure origin and we should return True
            return True

        # If we've gotten to this point, then the origin isn't secure and we
        # will not accept it as a valid location to search. We will however
        # log a warning that we are ignoring it.
        logger.warning(
            "The repository located at %s is not a trusted or secure host and "
            "is being ignored. If this repository is available via HTTPS we "
            "recommend you use HTTPS instead, otherwise you may silence "
            "this warning and allow it anyway with '--trusted-host %s'.",
            origin_host,
            origin_host,
        )

        return False

    def request(self, method, url, *args, **kwargs):
        # Allow setting a default timeout on a session
        kwargs.setdefault("timeout", self.timeout)

        # Dispatch the actual request
        return super(PipSession, self).request(method, url, *args, **kwargs)


def get_file_content(url, comes_from=None, session=None):
    # type: (str, Optional[str], Optional[PipSession]) -> Tuple[str, Text]
    """Gets the content of a file; it may be a filename, file: URL, or
    http: URL.  Returns (location, content).  Content is unicode.

    :param url:         File path or url.
    :param comes_from:  Origin description of requirements.
    :param session:     Instance of pip.download.PipSession.
    """
    if session is None:
        raise TypeError(
            "get_file_content() missing 1 required keyword argument: 'session'"
        )

    scheme = get_url_scheme(url)

    if scheme in ['http', 'https']:
        # FIXME: catch some errors
        resp = session.get(url)
        resp.raise_for_status()
        return resp.url, resp.text

    elif scheme == 'file':
        if comes_from and comes_from.startswith('http'):
            raise InstallationError(
                'Requirements file %s references URL %s, which is local'
                % (comes_from, url))

        path = url.split(':', 1)[1]
        path = path.replace('\\', '/')
        match = _url_slash_drive_re.match(path)
        if match:
            path = match.group(1) + ':' + path.split('|', 1)[1]
        path = urllib_parse.unquote(path)
        if path.startswith('/'):
            path = '/' + path.lstrip('/')
        url = path

    try:
        with open(url, 'rb') as f:
            content = auto_decode(f.read())
    except IOError as exc:
        raise InstallationError(
            'Could not open requirements file: %s' % str(exc)
        )
    return url, content


_url_slash_drive_re = re.compile(r'/*([a-z])\|', re.I)


def unpack_vcs_link(link, location):
    # type: (Link, str) -> None
    vcs_backend = _get_used_vcs_backend(link)
    assert vcs_backend is not None
    vcs_backend.unpack(location, url=hide_url(link.url))


def _get_used_vcs_backend(link):
    # type: (Link) -> Optional[VersionControl]
    """
    Return a VersionControl object or None.
    """
    for vcs_backend in vcs.backends:
        if link.scheme in vcs_backend.schemes:
            return vcs_backend
    return None


def is_file_url(link):
    # type: (Link) -> bool
    return link.url.lower().startswith('file:')


def is_dir_url(link):
    # type: (Link) -> bool
    """Return whether a file:// Link points to a directory.

    ``link`` must not have any other scheme but file://. Call is_file_url()
    first.

    """
    link_path = link.file_path
    return os.path.isdir(link_path)


def _progress_indicator(iterable, *args, **kwargs):
    return iterable


def _download_url(
    resp,  # type: Response
    link,  # type: Link
    content_file,  # type: IO
    hashes,  # type: Optional[Hashes]
    progress_bar  # type: str
):
    # type: (...) -> None
    try:
        total_length = int(resp.headers['content-length'])
    except (ValueError, KeyError, TypeError):
        total_length = 0

    cached_resp = getattr(resp, "from_cache", False)
    if logger.getEffectiveLevel() > logging.INFO:
        show_progress = False
    elif cached_resp:
        show_progress = False
    elif total_length > (40 * 1000):
        show_progress = True
    elif not total_length:
        show_progress = True
    else:
        show_progress = False

    show_url = link.show_url

    def resp_read(chunk_size):
        try:
            # Special case for urllib3.
            for chunk in resp.raw.stream(
                    chunk_size,
                    # We use decode_content=False here because we don't
                    # want urllib3 to mess with the raw bytes we get
                    # from the server. If we decompress inside of
                    # urllib3 then we cannot verify the checksum
                    # because the checksum will be of the compressed
                    # file. This breakage will only occur if the
                    # server adds a Content-Encoding header, which
                    # depends on how the server was configured:
                    # - Some servers will notice that the file isn't a
                    #   compressible file and will leave the file alone
                    #   and with an empty Content-Encoding
                    # - Some servers will notice that the file is
                    #   already compressed and will leave the file
                    #   alone and will add a Content-Encoding: gzip
                    #   header
                    # - Some servers won't notice anything at all and
                    #   will take a file that's already been compressed
                    #   and compress it again and set the
                    #   Content-Encoding: gzip header
                    #
                    # By setting this not to decode automatically we
                    # hope to eliminate problems with the second case.
                    decode_content=False):
                yield chunk
        except AttributeError:
            # Standard file-like object.
            while True:
                chunk = resp.raw.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    def written_chunks(chunks):
        for chunk in chunks:
            content_file.write(chunk)
            yield chunk

    progress_indicator = _progress_indicator

    if link.netloc == PyPI.netloc:
        url = show_url
    else:
        url = link.url_without_fragment

    if show_progress:  # We don't show progress on cached responses
        progress_indicator = DownloadProgressProvider(progress_bar,
                                                      max=total_length)
        if total_length:
            logger.info("Downloading %s (%s)", url, format_size(total_length))
        else:
            logger.info("Downloading %s", url)
    elif cached_resp:
        logger.info("Using cached %s", url)
    else:
        logger.info("Downloading %s", url)

    downloaded_chunks = written_chunks(
        progress_indicator(
            resp_read(CONTENT_CHUNK_SIZE),
            CONTENT_CHUNK_SIZE
        )
    )
    if hashes:
        hashes.check_against_chunks(downloaded_chunks)
    else:
        consume(downloaded_chunks)


def _copy_file(filename, location, link):
    copy = True
    download_location = os.path.join(location, link.filename)
    if os.path.exists(download_location):
        response = ask_path_exists(
            'The file %s exists. (i)gnore, (w)ipe, (b)ackup, (a)abort' %
            display_path(download_location), ('i', 'w', 'b', 'a'))
        if response == 'i':
            copy = False
        elif response == 'w':
            logger.warning('Deleting %s', display_path(download_location))
            os.remove(download_location)
        elif response == 'b':
            dest_file = backup_dir(download_location)
            logger.warning(
                'Backing up %s to %s',
                display_path(download_location),
                display_path(dest_file),
            )
            shutil.move(download_location, dest_file)
        elif response == 'a':
            sys.exit(-1)
    if copy:
        shutil.copy(filename, download_location)
        logger.info('Saved %s', display_path(download_location))


def unpack_http_url(
    link,  # type: Link
    location,  # type: str
    download_dir=None,  # type: Optional[str]
    session=None,  # type: Optional[PipSession]
    hashes=None,  # type: Optional[Hashes]
    progress_bar="on"  # type: str
):
    # type: (...) -> None
    if session is None:
        raise TypeError(
            "unpack_http_url() missing 1 required keyword argument: 'session'"
        )

    with TempDirectory(kind="unpack") as temp_dir:
        # If a download dir is specified, is the file already downloaded there?
        already_downloaded_path = None
        if download_dir:
            already_downloaded_path = _check_download_dir(link,
                                                          download_dir,
                                                          hashes)

        if already_downloaded_path:
            from_path = already_downloaded_path
            content_type = mimetypes.guess_type(from_path)[0]
        else:
            # let's download to a tmp dir
            from_path, content_type = _download_http_url(link,
                                                         session,
                                                         temp_dir.path,
                                                         hashes,
                                                         progress_bar)

        # unpack the archive to the build dir location. even when only
        # downloading archives, they have to be unpacked to parse dependencies
        unpack_file(from_path, location, content_type)

        # a download dir is specified; let's copy the archive there
        if download_dir and not already_downloaded_path:
            _copy_file(from_path, download_dir, link)

        if not already_downloaded_path:
            os.unlink(from_path)


def _copy2_ignoring_special_files(src, dest):
    # type: (str, str) -> None
    """Copying special files is not supported, but as a convenience to users
    we skip errors copying them. This supports tools that may create e.g.
    socket files in the project source directory.
    """
    try:
        copy2_fixed(src, dest)
    except shutil.SpecialFileError as e:
        # SpecialFileError may be raised due to either the source or
        # destination. If the destination was the cause then we would actually
        # care, but since the destination directory is deleted prior to
        # copy we ignore all of them assuming it is caused by the source.
        logger.warning(
            "Ignoring special file error '%s' encountered copying %s to %s.",
            str(e),
            path_to_display(src),
            path_to_display(dest),
        )


def _copy_source_tree(source, target):
    # type: (str, str) -> None
    def ignore(d, names):
        # Pulling in those directories can potentially be very slow,
        # exclude the following directories if they appear in the top
        # level dir (and only it).
        # See discussion at https://github.com/pypa/pip/pull/6770
        return ['.tox', '.nox'] if d == source else []

    kwargs = dict(ignore=ignore, symlinks=True)  # type: CopytreeKwargs

    if not PY2:
        # Python 2 does not support copy_function, so we only ignore
        # errors on special file copy in Python 3.
        kwargs['copy_function'] = _copy2_ignoring_special_files

    shutil.copytree(source, target, **kwargs)


def unpack_file_url(
    link,  # type: Link
    location,  # type: str
    download_dir=None,  # type: Optional[str]
    hashes=None  # type: Optional[Hashes]
):
    # type: (...) -> None
    """Unpack link into location.

    If download_dir is provided and link points to a file, make a copy
    of the link file inside download_dir.
    """
    link_path = link.file_path
    # If it's a url to a local directory
    if is_dir_url(link):
        if os.path.isdir(location):
            rmtree(location)
        _copy_source_tree(link_path, location)
        if download_dir:
            logger.info('Link is a directory, ignoring download_dir')
        return

    # If --require-hashes is off, `hashes` is either empty, the
    # link's embedded hash, or MissingHashes; it is required to
    # match. If --require-hashes is on, we are satisfied by any
    # hash in `hashes` matching: a URL-based or an option-based
    # one; no internet-sourced hash will be in `hashes`.
    if hashes:
        hashes.check_against_path(link_path)

    # If a download dir is specified, is the file already there and valid?
    already_downloaded_path = None
    if download_dir:
        already_downloaded_path = _check_download_dir(link,
                                                      download_dir,
                                                      hashes)

    if already_downloaded_path:
        from_path = already_downloaded_path
    else:
        from_path = link_path

    content_type = mimetypes.guess_type(from_path)[0]

    # unpack the archive to the build dir location. even when only downloading
    # archives, they have to be unpacked to parse dependencies
    unpack_file(from_path, location, content_type)

    # a download dir is specified and not already downloaded
    if download_dir and not already_downloaded_path:
        _copy_file(from_path, download_dir, link)


class PipXmlrpcTransport(xmlrpc_client.Transport):
    """Provide a `xmlrpclib.Transport` implementation via a `PipSession`
    object.
    """

    def __init__(self, index_url, session, use_datetime=False):
        xmlrpc_client.Transport.__init__(self, use_datetime)
        index_parts = urllib_parse.urlparse(index_url)
        self._scheme = index_parts.scheme
        self._session = session

    def request(self, host, handler, request_body, verbose=False):
        parts = (self._scheme, host, handler, None, None, None)
        url = urllib_parse.urlunparse(parts)
        try:
            headers = {'Content-Type': 'text/xml'}
            response = self._session.post(url, data=request_body,
                                          headers=headers, stream=True)
            response.raise_for_status()
            self.verbose = verbose
            return self.parse_response(response.raw)
        except requests.HTTPError as exc:
            logger.critical(
                "HTTP error %s while getting %s",
                exc.response.status_code, url,
            )
            raise


def unpack_url(
    link,  # type: Link
    location,  # type: str
    download_dir=None,  # type: Optional[str]
    session=None,  # type: Optional[PipSession]
    hashes=None,  # type: Optional[Hashes]
    progress_bar="on"  # type: str
):
    # type: (...) -> None
    """Unpack link.
       If link is a VCS link:
         if only_download, export into download_dir and ignore location
          else unpack into location
       for other types of link:
         - unpack into location
         - if download_dir, copy the file into download_dir
         - if only_download, mark location for deletion

    :param hashes: A Hashes object, one of whose embedded hashes must match,
        or HashMismatch will be raised. If the Hashes is empty, no matches are
        required, and unhashable types of requirements (like VCS ones, which
        would ordinarily raise HashUnsupported) are allowed.
    """
    # non-editable vcs urls
    if link.is_vcs:
        unpack_vcs_link(link, location)

    # file urls
    elif is_file_url(link):
        unpack_file_url(link, location, download_dir, hashes=hashes)

    # http urls
    else:
        if session is None:
            session = PipSession()

        unpack_http_url(
            link,
            location,
            download_dir,
            session,
            hashes=hashes,
            progress_bar=progress_bar
        )


def sanitize_content_filename(filename):
    # type: (str) -> str
    """
    Sanitize the "filename" value from a Content-Disposition header.
    """
    return os.path.basename(filename)


def parse_content_disposition(content_disposition, default_filename):
    # type: (str, str) -> str
    """
    Parse the "filename" value from a Content-Disposition header, and
    return the default filename if the result is empty.
    """
    _type, params = cgi.parse_header(content_disposition)
    filename = params.get('filename')
    if filename:
        # We need to sanitize the filename to prevent directory traversal
        # in case the filename contains ".." path parts.
        filename = sanitize_content_filename(filename)
    return filename or default_filename


def _download_http_url(
    link,  # type: Link
    session,  # type: PipSession
    temp_dir,  # type: str
    hashes,  # type: Optional[Hashes]
    progress_bar  # type: str
):
    # type: (...) -> Tuple[str, str]
    """Download link url into temp_dir using provided session"""
    target_url = link.url.split('#', 1)[0]
    try:
        resp = session.get(
            target_url,
            # We use Accept-Encoding: identity here because requests
            # defaults to accepting compressed responses. This breaks in
            # a variety of ways depending on how the server is configured.
            # - Some servers will notice that the file isn't a compressible
            #   file and will leave the file alone and with an empty
            #   Content-Encoding
            # - Some servers will notice that the file is already
            #   compressed and will leave the file alone and will add a
            #   Content-Encoding: gzip header
            # - Some servers won't notice anything at all and will take
            #   a file that's already been compressed and compress it again
            #   and set the Content-Encoding: gzip header
            # By setting this to request only the identity encoding We're
            # hoping to eliminate the third case. Hopefully there does not
            # exist a server which when given a file will notice it is
            # already compressed and that you're not asking for a
            # compressed file and will then decompress it before sending
            # because if that's the case I don't think it'll ever be
            # possible to make this work.
            headers={"Accept-Encoding": "identity"},
            stream=True,
        )
        resp.raise_for_status()
    except requests.HTTPError as exc:
        logger.critical(
            "HTTP error %s while getting %s", exc.response.status_code, link,
        )
        raise

    content_type = resp.headers.get('content-type', '')
    filename = link.filename  # fallback
    # Have a look at the Content-Disposition header for a better guess
    content_disposition = resp.headers.get('content-disposition')
    if content_disposition:
        filename = parse_content_disposition(content_disposition, filename)
    ext = splitext(filename)[1]  # type: Optional[str]
    if not ext:
        ext = mimetypes.guess_extension(content_type)
        if ext:
            filename += ext
    if not ext and link.url != resp.url:
        ext = os.path.splitext(resp.url)[1]
        if ext:
            filename += ext
    file_path = os.path.join(temp_dir, filename)
    with open(file_path, 'wb') as content_file:
        _download_url(resp, link, content_file, hashes, progress_bar)
    return file_path, content_type


def _check_download_dir(link, download_dir, hashes):
    # type: (Link, str, Optional[Hashes]) -> Optional[str]
    """ Check download_dir for previously downloaded file with correct hash
        If a correct file is found return its path else None
    """
    download_path = os.path.join(download_dir, link.filename)
    if os.path.exists(download_path):
        # If already downloaded, does its hash match?
        logger.info('File was already downloaded %s', download_path)
        if hashes:
            try:
                hashes.check_against_path(download_path)
            except HashMismatch:
                logger.warning(
                    'Previously-downloaded file %s has bad hash. '
                    'Re-downloading.',
                    download_path
                )
                os.unlink(download_path)
                return None
        return download_path
    return None
