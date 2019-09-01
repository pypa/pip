import textwrap


def test_environ(script, tmpdir):
    demo = tmpdir.joinpath('warnings_demo.py')
    demo.write_text(textwrap.dedent('''
        from logging import basicConfig
        from pip._internal.utils import deprecation

        deprecation.install_warning_logger()
        basicConfig()

        deprecation.deprecated("deprecated!", replacement=None, gone_in=None)
    '''))

    result = script.run('python', demo, expect_stderr=True)
    expected = 'WARNING:pip._internal.deprecations:DEPRECATION: deprecated!\n'
    assert result.stderr == expected

    # $PYTHONWARNINGS was added in python2.7
    script.environ['PYTHONWARNINGS'] = 'ignore'
    result = script.run('python', demo)
    assert result.stderr == ''
