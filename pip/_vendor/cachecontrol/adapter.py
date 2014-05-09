import functools

from pip._vendor.requests.adapters import HTTPAdapter

from .controller import CacheController
from .cache import DictCache
from .filewrapper import CallbackFileWrapper


class CacheControlAdapter(HTTPAdapter):
    invalidating_methods = set(['PUT', 'DELETE'])

    def __init__(self, cache=None, cache_etags=True, controller_class=None,
                 serializer=None, *args, **kw):
        super(CacheControlAdapter, self).__init__(*args, **kw)
        self.cache = cache or DictCache()

        controller_factory = controller_class or CacheController
        self.controller = controller_factory(
            self.cache,
            cache_etags=cache_etags,
            serializer=serializer,
        )

    def send(self, request, **kw):
        """
        Send a request. Use the request information to see if it
        exists in the cache and cache the response if we need to and can.
        """
        if request.method == 'GET':
            cached_response = self.controller.cached_request(request)
            if cached_response:
                return self.build_response(request, cached_response, from_cache=True)

            # check for etags and add headers if appropriate
            request.headers.update(self.controller.conditional_headers(request))

        resp = super(CacheControlAdapter, self).send(request, **kw)

        return resp

    def build_response(self, request, response, from_cache=False):
        """
        Build a response by making a request or using the cache.

        This will end up calling send and returning a potentially
        cached response
        """
        if not from_cache and request.method == 'GET':
            if response.status == 304:
                # We must have sent an ETag request. This could mean
                # that we've been expired already or that we simply
                # have an etag. In either case, we want to try and
                # update the cache if that is the case.
                cached_response = self.controller.update_cached_response(
                    request, response
                )

                if cached_response is not response:
                    from_cache = True

                response = cached_response
            else:
                # Wrap the response file with a wrapper that will cache the
                #   response when the stream has been consumed.
                response._fp = CallbackFileWrapper(
                    response._fp,
                    functools.partial(
                        self.controller.cache_response,
                        request,
                        response,
                    )
                )

        resp = super(CacheControlAdapter, self).build_response(
            request, response
        )

        # See if we should invalidate the cache.
        if request.method in self.invalidating_methods and resp.ok:
            cache_url = self.controller.cache_url(request.url)
            self.cache.delete(cache_url)

        # Give the request a from_cache attr to let people use it
        resp.from_cache = from_cache

        return resp
