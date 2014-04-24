import io

from pip._vendor.requests.structures import CaseInsensitiveDict

from .compat import HTTPResponse, pickle


class Serializer(object):

    def dumps(self, request, response, body=None):
        response_headers = CaseInsensitiveDict(response.headers)

        if body is None:
            body = response.read(decode_content=False)
            response._fp = io.BytesIO(body)

        data = {
            "response": {
                "body": body,
                "headers": response.headers,
                "status": response.status,
                "version": response.version,
                "reason": response.reason,
                "strict": response.strict,
                "decode_content": response.decode_content,
            },
        }

        # Construct our vary headers
        data["vary"] = {}
        if "vary" in response_headers:
            varied_headers = response_headers['vary'].split(',')
            for header in varied_headers:
                header = header.strip()
                data["vary"][header] = request.headers.get(header, None)

        return b"cc=1," + pickle.dumps(data, pickle.HIGHEST_PROTOCOL)

    def loads(self, request, data):
        # Short circuit if we've been given an empty set of data
        if not data:
            return

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
        ver = ver.split(b"=", 1)[-1].decode("ascii")

        # Dispatch to the actual load method for the given version
        try:
            return getattr(self, "_loads_v{0}".format(ver))(request, data)
        except AttributeError:
            # This is a version we don't have a loads function for, so we'll
            # just treat it as a miss and return None
            return

    def _loads_v0(self, request, data):
        # The original legacy cache data. This doesn't contain enough
        # information to construct everything we need, so we'll treat this as
        # a miss.
        return

    def _loads_v1(self, request, data):
        try:
            cached = pickle.loads(data)
        except ValueError:
            return

        # Special case the '*' Vary value as it means we cannot actually
        # determine if the cached response is suitable for this request.
        if "*" in cached.get("vary", {}):
            return

        # Ensure that the Vary headers for the cached response match our
        # request
        for header, value in cached.get("vary", {}).items():
            if request.headers.get(header, None) != value:
                return

        body = io.BytesIO(cached["response"].pop("body"))
        return HTTPResponse(
            body=body,
            preload_content=False,
            **cached["response"]
        )
