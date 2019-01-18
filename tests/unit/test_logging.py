import logging
import os
import time

from pip._internal.utils.logging import IndentingFormatter


class Test_IndentingFormatter(object):
    """
    Test `pip._internal.utils.logging.IndentingFormatter`
    """

    def setup(self):
        self.old_tz = getattr(os.environ, 'TZ', None)
        os.environ['TZ'] = 'UTC'
        if 'tzset' in dir(time):
            time.tzset()

    def teardown(self):
        if self.old_tz:
            os.environ['TZ'] = self.old_tz
        else:
            del os.environ['TZ']
        if 'tzset' in dir(time):
            time.tzset()

    def test_formatter_with_timestamp(self, tmpdir):
        record = logging.makeLogRecord(dict(
            created=1547704837.4,
            msg='hello\nworld',
        ))
        f = IndentingFormatter(fmt="%(message)s", timestamp=True)
        assert (f.format(record) ==
                '2019-01-17T06:00:37 hello\n2019-01-17T06:00:37 world')

    def test_formatter_without_timestamp(self, tmpdir):
        record = logging.makeLogRecord(dict(
            created=1547704837.4,
            msg='hello\nworld',
        ))
        f = IndentingFormatter(fmt="%(message)s", timestamp=False)
        assert f.format(record) == 'hello\nworld'
