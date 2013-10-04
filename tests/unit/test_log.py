try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO

from pip.log import should_color, should_warn, Logger


def test_should_color_std():
    assert not should_color(object(), {}, std=[object()])


def test_should_color_isatty():
    class FakeTTY(object):
        def isatty(self):
            return True

    consumer = FakeTTY()
    assert should_color(consumer, {}, std=[consumer])


def test_should_color_environ():
    consumer = object()
    assert should_color(consumer, {"TERM": "ANSI"}, std=[consumer])


def test_should_color_notty_environ():
    consumer = object()
    assert not should_color(consumer, {}, std=[consumer])


def test_should_warn_greater_one_minor():
    assert should_warn("1.4", "1.6")


def test_should_warn_exactly_one_minor():
    assert not should_warn("1.5", "1.6")


def test_should_warn_equal():
    assert not should_warn("1.6", "1.6")


def test_should_warn_greater():
    assert not should_warn("1.7", "1.6")


def test_should_warn_significance():
    assert should_warn("1.4.dev1", "1.6")


def test_log_no_extra_line_break():
    """
    Confirm that multiple `.write()` consumers doesn't result in additional '\n's per write
    """
    consumer1 = StringIO()
    consumer2 = StringIO()
    logger = Logger()
    logger.add_consumers(
            (logger.NOTIFY, consumer1),
            (logger.NOTIFY, consumer2)
            )
    logger.notify("one line")
    # splitlines(True) will detect empty line-breaks
    assert 1 == len(consumer1.getvalue().splitlines(True))
    assert 1 == len(consumer2.getvalue().splitlines(True))

