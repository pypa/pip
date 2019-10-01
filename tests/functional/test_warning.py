import textwrap

import pytest


@pytest.fixture
def warnings_demo(tmpdir):
    demo = tmpdir.joinpath('warnings_demo.py')
    demo.write_text(
        textwrap.dedent('''
        from logging import basicConfig
        from pip._internal.utils import deprecation

        deprecation.install_warning_logger()
        basicConfig()

        deprecation.deprecated("deprecated!", replacement=None, gone_in=None)
    '''),
    )
    return demo


def test_deprecation_warnings_are_correct(script, warnings_demo):
    result = script.run('python', warnings_demo, expect_stderr=True)
    expected = 'WARNING:pip._internal.deprecations:DEPRECATION: deprecated!\n'
    assert result.stderr == expected


def test_deprecation_warnings_can_be_silenced(script, warnings_demo):
    script.environ['PYTHONWARNINGS'] = 'ignore'
    result = script.run('python', warnings_demo)
    assert result.stderr == ''
