import os
from tests.test_pip import here, reset_env, run_pip


def test_install_package_that_emits_unicode():
    """
    Install a package with a setup.py that emits UTF-8 output and then fails.
    This works fine in Python 2, but fails in Python 3 with:

    Traceback (most recent call last):
      ...
      File "/Users/marc/python/virtualenvs/py3.1-phpserialize/lib/python3.2/site-packages/pip-1.0.2-py3.2.egg/pip/__init__.py", line 230, in call_subprocess
        line = console_to_str(stdout.readline())
      File "/Users/marc/python/virtualenvs/py3.1-phpserialize/lib/python3.2/site-packages/pip-1.0.2-py3.2.egg/pip/backwardcompat.py", line 60, in console_to_str
        return s.decode(console_encoding)
    UnicodeDecodeError: 'ascii' codec can't decode byte 0xe2 in position 17: ordinal not in range(128)

    Refs https://github.com/pypa/pip/issues/326
    """

    env = reset_env()
    to_install = os.path.abspath(os.path.join(here, 'packages', 'BrokenEmitsUTF8'))
    result = run_pip('install', to_install, expect_error=True)
    assert '__main__.FakeError: this package designed to fail on install' in result.stdout
    assert 'UnicodeDecodeError' not in result.stdout
