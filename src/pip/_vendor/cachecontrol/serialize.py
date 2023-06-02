# SPDX-FileCopyrightText: 2015 Eric Larson
#
# SPDX-License-Identifier: Apache-2.0

import base64
import io
import json
import pickle
import zlib
from typing import IO, TYPE_CHECKING, Any, Mapping, Optional

from pip._vendor import msgpack
from pip._vendor.requests.structures import CaseInsensitiveDict
from pip._vendor.urllib3 import HTTPResponse

if TYPE_CHECKING:
    from pip._vendor.requests import PreparedRequest, Request


def _b64_decode_bytes(b: str) -> bytes:
    return base64.b64decode(b.encode("ascii"))


def _b64_decode_str(s: str) -> str:
    return _b64_decode_bytes(s).decode("utf8")


_default_body_read = object()


class Serializer(object):
    def dumps(
        self,
        request: "PreparedRequest",
        response: HTTPResponse,
        body: Optional[bytes] = None,
    ) -> bytes:
        response_headers: CaseInsensitiveDict[str] = CaseInsensitiveDict(
            response.headers
        )

        if body is None:
            # When a body isn't passed in, we'll read the response. We
            # also update the response with a new file handler to be
            # sure it acts as though it was never read.
            body = response.read(decode_content=False)
            response._fp = io.BytesIO(body)  # type: ignore[attr-defined]
            response.length_remaining = len(body)

        data = {
            "response": {
                "body": body,  # Empty bytestring if body is stored separately
                "headers": dict((str(k), str(v)) for k, v in response.headers.items()),  # type: ignore[no-untyped-call]
                "status": response.status,
                "version": response.version,
                "reason": str(response.reason),
                "decode_content": response.decode_content,
            }
        }

        # Construct our vary headers
        data["vary"] = {}
        if "vary" in response_headers:
            varied_headers = response_headers["vary"].split(",")
            for header in varied_headers:
                header = str(header).strip()
                header_value = request.headers.get(header, None)
                if header_value is not None:
                    header_value = str(header_value)
                data["vary"][header] = header_value

        return b",".join([b"cc=4", msgpack.dumps(data, use_bin_type=True)])

    def loads(
        self,
        request: "PreparedRequest",
        data: bytes,
        body_file: Optional["IO[bytes]"] = None,
    ) -> Optional[HTTPResponse]:
        # Short circuit if we've been given an empty set of data
        if not data:
            return None

        # Determine what version of the serializer the data was serialized
        # with
        try:
            ver, data = data.split(b",", 1)
        except ValueError:
            ver = b"cc=0"

        # Make sure that our "ver" is actually a version and isn't a false
        # positive from a , being in the data stream.
        if ver[:3] != b"cc=":
            data = ver + data
            ver = b"cc=0"

        # Get the version number out of the cc=N
        verstr = ver.split(b"=", 1)[-1].decode("ascii")

        # Dispatch to the actual load method for the given version
        try:
            return getattr(self, "_loads_v{}".format(verstr))(request, data, body_file)  # type: ignore[no-any-return]

        except AttributeError:
            # This is a version we don't have a loads function for, so we'll
            # just treat it as a miss and return None
            return None

    def prepare_response(
        self,
        request: "Request",
        cached: Mapping[str, Any],
        body_file: Optional["IO[bytes]"] = None,
    ) -> Optional[HTTPResponse]:
        """Verify our vary headers match and construct a real urllib3
        HTTPResponse object.
        """
        # Special case the '*' Vary value as it means we cannot actually
        # determine if the cached response is suitable for this request.
        # This case is also handled in the controller code when creating
        # a cache entry, but is left here for backwards compatibility.
        if "*" in cached.get("vary", {}):
            return None

        # Ensure that the Vary headers for the cached response match our
        # request
        for header, value in cached.get("vary", {}).items():
            if request.headers.get(header, None) != value:
                return None

        body_raw = cached["response"].pop("body")

        headers: CaseInsensitiveDict[str] = CaseInsensitiveDict(
            data=cached["response"]["headers"]
        )
        if headers.get("transfer-encoding", "") == "chunked":
            headers.pop("transfer-encoding")

        cached["response"]["headers"] = headers

        try:
            body: "IO[bytes]"
            if body_file is None:
                body = io.BytesIO(body_raw)
            else:
                body = body_file
        except TypeError:
            # This can happen if cachecontrol serialized to v1 format (pickle)
            # using Python 2. A Python 2 str(byte string) will be unpickled as
            # a Python 3 str (unicode string), which will cause the above to
            # fail with:
            #
            #     TypeError: 'str' does not support the buffer interface
            body = io.BytesIO(body_raw.encode("utf8"))

        # Discard any `strict` parameter serialized by older version of cachecontrol.
        cached["response"].pop("strict", None)

        return HTTPResponse(body=body, preload_content=False, **cached["response"])

    def _loads_v0(
        self,
        request: "Request",
        data: bytes,
        body_file: Optional["IO[bytes]"] = None,
    ) -> None:
        # The original legacy cache data. This doesn't contain enough
        # information to construct everything we need, so we'll treat this as
        # a miss.
        return

    def _loads_v1(
        self,
        request: "Request",
        data: bytes,
        body_file: Optional["IO[bytes]"] = None,
    ) -> Optional[HTTPResponse]:
        try:
            cached = pickle.loads(data)
        except ValueError:
            return None

        return self.prepare_response(request, cached, body_file)

    def _loads_v2(
        self,
        request: "Request",
        data: bytes,
        body_file: Optional["IO[bytes]"] = None,
    ) -> Optional[HTTPResponse]:
        assert body_file is None
        try:
            cached = json.loads(zlib.decompress(data).decode("utf8"))
        except (ValueError, zlib.error):
            return None

        # We need to decode the items that we've base64 encoded
        cached["response"]["body"] = _b64_decode_bytes(cached["response"]["body"])
        cached["response"]["headers"] = dict(
            (_b64_decode_str(k), _b64_decode_str(v))
            for k, v in cached["response"]["headers"].items()
        )
        cached["response"]["reason"] = _b64_decode_str(cached["response"]["reason"])
        cached["vary"] = dict(
            (_b64_decode_str(k), _b64_decode_str(v) if v is not None else v)
            for k, v in cached["vary"].items()
        )

        return self.prepare_response(request, cached, body_file)

    def _loads_v3(
        self,
        request: "Request",
        data: bytes,
        body_file: Optional["IO[bytes]"] = None,
    ) -> None:
        # Due to Python 2 encoding issues, it's impossible to know for sure
        # exactly how to load v3 entries, thus we'll treat these as a miss so
        # that they get rewritten out as v4 entries.
        return

    def _loads_v4(
        self,
        request: "Request",
        data: bytes,
        body_file: Optional["IO[bytes]"] = None,
    ) -> Optional[HTTPResponse]:
        try:
            cached = msgpack.loads(data, raw=False)
        except ValueError:
            return None

        return self.prepare_response(request, cached, body_file)
