# For backwards compatibility, provide imports that used to be here.
from .connection import is_connection_dropped
from .request import make_headers
from .response import is_fp_closed
from .retry import Retry
from .ssl_ import (
    HAS_SNI,
    SSLContext,
    assert_fingerprint,
    resolve_cert_reqs,
    resolve_ssl_version,
    ssl_wrap_socket,
)
from .timeout import Timeout, current_time
from .url import Url, get_host, parse_url, split_first
