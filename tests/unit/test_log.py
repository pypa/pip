from pip.compat import StringIO
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


def test_ignores_duplicate_consumers():
    """
    Make sure if the same consumer & level pair are asked to be added,
    they're ignored.
    """
    logger = Logger()

    import sys
    consumer1 = sys.stdout
    consumer2 = sys.stdout

    logger.add_consumers(
        (logger.NOTIFY, consumer1),
        (logger.NOTIFY, consumer2),
    )
    logger.add_consumers(
        (logger.NOTIFY, consumer1),
        (logger.NOTIFY, consumer2),
    )

    assert 1 == len(logger.consumers)


def test_ignores_Win32_wrapped_consumers(monkeypatch):
    """
    Test that colorama wrapped duplicate streams are ignored, too.
    """
    logger = Logger()
    consumer = StringIO()

    consumer1 = consumer
    consumer2 = consumer

    # Pretend to be Windows
    monkeypatch.setattr('sys.platform', 'win32')
    logger.add_consumers(
        (logger.NOTIFY, consumer1),
        (logger.NOTIFY, consumer2),
    )
    # Pretend to be linux
    monkeypatch.setattr('sys.platform', 'linux2')
    logger.add_consumers(
        (logger.NOTIFY, consumer2),
        (logger.NOTIFY, consumer1),
    )

    assert 1 == len(logger.consumers)


def test_log_no_extra_line_break():
    """
    Confirm that multiple `.write()` consumers doesn't result in additional
    '\n's per write
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


def test_level_for_integer():
    logger = Logger()
    assert logger.VERBOSE_DEBUG == logger.level_for_integer(-1000)
    assert logger.VERBOSE_DEBUG == logger.level_for_integer(0)
    assert logger.DEBUG == logger.level_for_integer(1)
    assert logger.INFO == logger.level_for_integer(2)
    assert logger.NOTIFY == logger.level_for_integer(3)
    assert logger.WARN == logger.level_for_integer(4)
    assert logger.ERROR == logger.level_for_integer(5)
    assert logger.FATAL == logger.level_for_integer(6)
    assert logger.FATAL == logger.level_for_integer(1000)
