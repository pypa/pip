import logging
import os
import time

from pip._internal.utils.logging import IndentingFormatter


class TestIndentingFormatter(object):
    """
    Test `pip._internal.utils.logging.IndentingFormatter`.
    """

    def setup(self):
        # Robustify the tests below to the ambient timezone by setting it
        # explicitly here.
        self.old_tz = getattr(os.environ, 'TZ', None)
        os.environ['TZ'] = 'UTC'
        # time.tzset() is not implemented on some platforms (notably, Windows).
        if hasattr(time, 'tzset'):
            time.tzset()

    def teardown(self):
        if self.old_tz:
            os.environ['TZ'] = self.old_tz
        else:
            del os.environ['TZ']
        if 'tzset' in dir(time):
            time.tzset()

    def test_format(self, tmpdir):
        record = logging.makeLogRecord(dict(
            created=1547704837.4,
            msg='hello\nworld',
        ))
        f = IndentingFormatter(fmt="%(message)s")
        assert f.format(record) == 'hello\nworld'

    def test_format_with_timestamp(self, tmpdir):
        record = logging.makeLogRecord(dict(
            created=1547704837.4,
            msg='hello\nworld',
        ))
        f = IndentingFormatter(fmt="%(message)s", add_timestamp=True)
        expected = '2019-01-17T06:00:37 hello\n2019-01-17T06:00:37 world'
        assert f.format(record) == expected
