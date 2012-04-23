import sys
import re
import textwrap
from doctest import OutputChecker, ELLIPSIS
from tests.test_pip import reset_env, run_pip, write_file, get_env, pyversion
from tests.local_repos import local_checkout, local_repo


distribute_re = re.compile('^distribute==[0-9.]+\n', re.MULTILINE)


def _check_output(result, expected):
    checker = OutputChecker()
    actual = str(result)

    ## FIXME!  The following is a TOTAL hack.  For some reason the
    ## __str__ result for pkg_resources.Requirement gets downcased on
    ## Windows.  Since INITools is the only package we're installing
    ## in this file with funky case requirements, I'm forcibly
    ## upcasing it.  You can also normalize everything to lowercase,
    ## but then you have to remember to upcase <BLANKLINE>.  The right
    ## thing to do in the end is probably to find out how to report
    ## the proper fully-cased package name in our error message.
    if sys.platform == 'win32':
        actual = actual.replace('initools', 'INITools')

    # This allows our existing tests to work when run in a context
    # with distribute installed.
    actual = distribute_re.sub('', actual)

    def banner(msg):
        return '\n========== %s ==========\n' % msg
    assert checker.check_output(expected, actual, ELLIPSIS), banner('EXPECTED')+expected+banner('ACTUAL')+actual+banner(6*'=')

def test_show():
    env = reset_env()
    write_file('requires.txt', textwrap.dedent("""\
        INITools==0.2
        """))
    result = run_pip('install', '-r', env.scratch_path/'requires.txt')
    result = run_pip('show', 'INITools', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: pip show INITools
        -- stdout: --------------------
        Package: INITools
        Version: 0.2
        """)
    _check_output(result, expected)

