from pip.log import should_color, should_warn


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
