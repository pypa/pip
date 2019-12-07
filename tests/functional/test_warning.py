import textwrap

import pytest


@pytest.fixture
def warnings_demo(tmpdir):
    demo = tmpdir.joinpath('warnings_demo.py')
    demo.write_text(textwrap.dedent('''
        from logging import basicConfig
        from pip._internal.utils import deprecation

        deprecation.install_warning_logger()
        basicConfig()

        deprecation.deprecated("deprecated!", replacement=None, gone_in=None)
    '''))
    return demo


def test_deprecation_warnings_are_correct(script, warnings_demo):
    result = script.run('python', warnings_demo, expect_stderr=True)
    expected = 'WARNING:pip._internal.deprecations:DEPRECATION: deprecated!\n'
    assert result.stderr == expected


def test_deprecation_warnings_can_be_silenced(script, warnings_demo):
    script.environ['PYTHONWARNINGS'] = 'ignore'
    result = script.run('python', warnings_demo)
    assert result.stderr == ''


deprecation_message = "DEPRECATION: Python 2.7 will reach the" \
                      " end of its life on January 1st, 2020." \
                      " Please upgrade your Python as Python 2.7" \
                      " won't be maintained after that date. " \
                      "A future version of pip will drop support" \
                      " for Python 2.7. More details about Python 2" \
                      " support in pip, can be found at" \
                      " https://pip.pypa.io/en/latest/development/release-process/#python-2-support"  # noqa


@pytest.mark.skipif(
    "sys.version_info[:2] in [(2, 7)] "
    "and platform.python_implementation() == 'CPython'")
def test_version_warning_is_not_shown_if_python_version_is_not_27(script):
    result = script.pip("debug", allow_stderr_warning=True)
    assert deprecation_message not in result.stderr, str(result)


@pytest.mark.skipif(
    "not (sys.version_info[:2] in [(2, 7)] "
    "and platform.python_implementation() == 'CPython')")
def test_version_warning_is_shown_if_python_version_is_27(script):
    result = script.pip("debug", allow_stderr_warning=True)
    assert deprecation_message in result.stderr, str(result)


@pytest.mark.skipif(
    "not (sys.version_info[:2] in [(2, 7)] "
    "and platform.python_implementation() == 'CPython')")
def test_version_warning_is_not_shown_when_flag_is_passed(script):
    result = script.pip(
        "debug", "--no-python-version-warning", allow_stderr_warning=True
    )
    assert deprecation_message not in result.stderr, str(result)
    assert "--no-python-version-warning" not in result.stderr
