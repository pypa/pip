import calendar

from email.utils import formatdate, parsedate

from datetime import datetime, timedelta


def expire_after(delta, date=None):
    date = date or datetime.now()
    return date + delta


def datetime_to_header(dt):
    return formatdate(calendar.timegm(dt.timetuple()))


class BaseHeuristic(object):

    def warning(self, response):
        """
        Return a valid 1xx warning header value describing the cache adjustments.

        The response is provided too allow warnings like 113
        http://tools.ietf.org/html/rfc7234#section-5.5.4 where we need
        to explicitly say response is over 24 hours old.
        """
        return '110 - "Response is Stale"'

    def update_headers(self, response):
        """Update the response headers with any new headers.

        NOTE: This SHOULD always include some Warning header to
              signify that the response was cached by the client, not
              by way of the provided headers.
        """
        return {}

    def apply(self, response):
        warning_header = {'warning': self.warning(response)}
        response.headers.update(self.update_headers(response))
        response.headers.update(warning_header)
        return response


class OneDayCache(BaseHeuristic):
    """
    Cache the response by providing an expires 1 day in the
    future.
    """
    def update_headers(self, response):
        headers = {}

        if 'expires' not in response.headers:
            date = parsedate(response.headers['date'])
            expires = expire_after(timedelta(days=1),
                                   date=datetime(*date[:6]))
            headers['expires'] = datetime_to_header(expires)
            headers['cache-control'] = 'public'
        return headers


class ExpiresAfter(BaseHeuristic):
    """
    Cache **all** requests for a defined time period.
    """

    def __init__(self, **kw):
        self.delta = timedelta(**kw)

    def update_headers(self, response):
        expires = expire_after(self.delta)
        return {
            'expires': datetime_to_header(expires),
            'cache-control': 'public',
        }

    def warning(self, response):
        tmpl = '110 - Automatically cached for %s. Response might be stale'
        return tmpl % self.delta
