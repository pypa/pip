import logging
import re
import time

from pip._internal.utils.logging import IndentingFormatter

class Test_IndentingFormatter(object):
    """
    Test `pip._internal.utils.logging.IndentingFormatter`
    """

    def test_formatter_with_timestamp(self, tmpdir):
        record = logging.makeLogRecord(dict(
            created=1547704837.4,
            msg='hello\nworld',
        ))
        f = IndentingFormatter(fmt="%(message)s", timestamp=True)
        assert f.format(record) == '2019-01-16T22:00:37 hello\n2019-01-16T22:00:37 world'

    def test_formatter_without_timestamp(self, tmpdir):
        record = logging.makeLogRecord(dict(
            created=1547704837.4,
            msg='hello\nworld',
        ))
        f = IndentingFormatter(fmt="%(message)s", timestamp=False)
        assert f.format(record) == 'hello\nworld'
