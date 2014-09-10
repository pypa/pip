import calendar

from email.utils import formatdate, parsedate

from datetime import datetime, timedelta


class BaseHeuristic(object):

    def warning(self):
        """
        Return a valid 1xx warning header value describing the cache adjustments.
        """
        return '110 - "Response is Stale"'

    def update_headers(self, response):
        """Update the response headers with any new headers.

        NOTE: This SHOULD always include some Warning header to
              signify that the response was cached by the client, not by way
              of the provided headers.
              return response.
        """
        return {}

    def apply(self, response):
        response.headers.update(self.update_headers(response))
        response.headers.update({'warning': self.warning()})
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
            expires = datetime(*date[:6]) + timedelta(days=1)
            headers['expires'] = formatdate(calendar.timegm(expires.timetuple()))

        return headers
