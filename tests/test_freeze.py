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


def test_freeze_basic():
    """
    Some tests of freeze, first we have to install some stuff.  Note that
    the test is a little crude at the end because Python 2.5+ adds egg
    info to the standard library, so stuff like wsgiref will show up in
    the freezing.  (Probably that should be accounted for in pip, but
    currently it is not).

    """
    env = reset_env()
    write_file('initools-req.txt', textwrap.dedent("""\
        INITools==0.2
        # and something else to test out:
        MarkupSafe<=0.12
        """))
    result = run_pip('install', '-r', env.scratch_path/'initools-req.txt')
    result = run_pip('freeze', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: pip freeze
        -- stdout: --------------------
        INITools==0.2
        MarkupSafe==0.12...
        <BLANKLINE>""")
    _check_output(result, expected)


def test_freeze_svn():
    """Now lets try it with an svn checkout"""
    env = reset_env()
    result = env.run('svn', 'co', '-r10',
                     local_repo('svn+http://svn.colorstudy.com/INITools/trunk'),
                     'initools-trunk')
    result = env.run('python', 'setup.py', 'develop',
            cwd=env.scratch_path/ 'initools-trunk')
    result = run_pip('freeze', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze
        -- stdout: --------------------
        -e %s@10#egg=INITools-0.3.1dev_r10-py...-dev_r10
        ...""" % local_checkout('svn+http://svn.colorstudy.com/INITools/trunk'))
    _check_output(result, expected)


def test_freeze_git_clone():
    """
    Test freezing a Git clone.

    """
    env = reset_env()
    result = env.run('git', 'clone', local_repo('git+http://github.com/pypa/pip-test-package.git'), 'pip-test-package')
    result = env.run('git', 'checkout', '7d654e66c8fa7149c165ddeffa5b56bc06619458',
            cwd=env.scratch_path / 'pip-test-package', expect_stderr=True)
    result = env.run('python', 'setup.py', 'develop',
            cwd=env.scratch_path / 'pip-test-package')
    result = run_pip('freeze', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze
        -- stdout: --------------------
        -e %s@...#egg=pip_test_package-...
        ...""" % local_checkout('git+http://github.com/pypa/pip-test-package.git'))
    _check_output(result, expected)

    result = run_pip('freeze', '-f',
                     '%s#egg=pip_test_package' % local_checkout('git+http://github.com/pypa/pip-test-package.git'),
                     expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: pip freeze -f %(repo)s#egg=pip_test_package
        -- stdout: --------------------
        -f %(repo)s#egg=pip_test_package
        -e %(repo)s@...#egg=pip_test_package-dev
        ...""" % {'repo': local_checkout('git+http://github.com/pypa/pip-test-package.git')})
    _check_output(result, expected)


def test_freeze_mercurial_clone():
    """
    Test freezing a Mercurial clone.

    """
    reset_env()
    env = get_env()
    result = env.run('hg', 'clone',
                     '-r', '7bc186caa7dc',
                     local_repo('hg+http://bitbucket.org/jezdez/django-authority'),
                     'django-authority')
    result = env.run('python', 'setup.py', 'develop',
            cwd=env.scratch_path/'django-authority', expect_stderr=True)
    result = run_pip('freeze', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze
        -- stdout: --------------------
        -e %s@...#egg=django_authority-...
        ...""" % local_checkout('hg+http://bitbucket.org/jezdez/django-authority'))
    _check_output(result, expected)

    result = run_pip('freeze', '-f',
                     '%s#egg=django_authority' % local_checkout('hg+http://bitbucket.org/jezdez/django-authority'),
                     expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze -f %(repo)s#egg=django_authority
        -- stdout: --------------------
        -f %(repo)s#egg=django_authority
        -e %(repo)s@...#egg=django_authority-dev
        ...""" % {'repo': local_checkout('hg+http://bitbucket.org/jezdez/django-authority')})
    _check_output(result, expected)


def test_freeze_bazaar_clone():
    """
    Test freezing a Bazaar clone.

    """
    reset_env()
    env = get_env()
    result = env.run('bzr', 'checkout', '-r', '174',
                     local_repo('bzr+http://bazaar.launchpad.net/%7Edjango-wikiapp/django-wikiapp/release-0.1'),
                     'django-wikiapp')
    result = env.run('python', 'setup.py', 'develop',
            cwd=env.scratch_path/'django-wikiapp')
    result = run_pip('freeze', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze
        -- stdout: --------------------
        -e %s@...#egg=django_wikiapp-...
        ...""" % local_checkout('bzr+http://bazaar.launchpad.net/%7Edjango-wikiapp/django-wikiapp/release-0.1'))
    _check_output(result, expected)

    result = run_pip('freeze', '-f',
                     '%s/#egg=django-wikiapp' %
                     local_checkout('bzr+http://bazaar.launchpad.net/%7Edjango-wikiapp/django-wikiapp/release-0.1'),
                     expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze -f %(repo)s/#egg=django-wikiapp
        -- stdout: --------------------
        -f %(repo)s/#egg=django-wikiapp
        -e %(repo)s@...#egg=django_wikiapp-...
        ...""" % {'repo':
                  local_checkout('bzr+http://bazaar.launchpad.net/%7Edjango-wikiapp/django-wikiapp/release-0.1')})
    _check_output(result, expected)


def test_freeze_with_local_option():
    """
    Test that wsgiref (from global site-packages) is reported normally, but not with --local.

    """
    reset_env()
    result = run_pip('install', 'initools==0.2')
    result = run_pip('freeze', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze
        -- stdout: --------------------
        INITools==0.2
        wsgiref==...
        <BLANKLINE>""")

    # The following check is broken (see
    # http://bitbucket.org/ianb/pip/issue/110).  For now we are simply
    # neutering this test, but if we can't find a way to fix it,
    # this whole function should be removed.

    # _check_output(result, expected)

    result = run_pip('freeze', '--local', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze --local
        -- stdout: --------------------
        INITools==0.2
        <BLANKLINE>""")
    _check_output(result, expected)
