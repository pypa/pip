import sys
import re
import textwrap
from doctest import OutputChecker, ELLIPSIS

from tests.lib.local_repos import local_checkout, local_repo


distribute_re = re.compile('^distribute==[0-9.]+\n', re.MULTILINE)


def _check_output(result, expected):
    checker = OutputChecker()
    actual = str(result)

    # FIXME!  The following is a TOTAL hack.  For some reason the
    # __str__ result for pkg_resources.Requirement gets downcased on
    # Windows.  Since INITools is the only package we're installing
    # in this file with funky case requirements, I'm forcibly
    # upcasing it.  You can also normalize everything to lowercase,
    # but then you have to remember to upcase <BLANKLINE>.  The right
    # thing to do in the end is probably to find out how to report
    # the proper fully-cased package name in our error message.
    if sys.platform == 'win32':
        actual = actual.replace('initools', 'INITools')

    # This allows our existing tests to work when run in a context
    # with distribute installed.
    actual = distribute_re.sub('', actual)

    def banner(msg):
        return '\n========== %s ==========\n' % msg

    assert checker.check_output(expected, actual, ELLIPSIS), (
        banner('EXPECTED') + expected + banner('ACTUAL') + actual +
        banner(6 * '=')
    )


def test_freeze_basic(script):
    """
    Some tests of freeze, first we have to install some stuff.  Note that
    the test is a little crude at the end because Python 2.5+ adds egg
    info to the standard library, so stuff like wsgiref will show up in
    the freezing.  (Probably that should be accounted for in pip, but
    currently it is not).

    """
    script.scratch_path.join("initools-req.txt").write(textwrap.dedent("""\
        simple==2.0
        # and something else to test out:
        simple2<=3.0
        """))
    script.pip_install_local(
        '-r', script.scratch_path / 'initools-req.txt',
    )
    result = script.pip('freeze', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: pip freeze
        -- stdout: --------------------
        ...simple==2.0
        simple2==3.0...
        <BLANKLINE>""")
    _check_output(result, expected)


def test_freeze_svn(script, tmpdir):
    """Test freezing a svn checkout"""

    checkout_path = local_checkout(
        'svn+http://svn.colorstudy.com/INITools/trunk',
        tmpdir.join("cache"),
    )
    # svn internally stores windows drives as uppercase; we'll match that.
    checkout_path = checkout_path.replace('c:', 'C:')

    # Checkout
    script.run(
        'svn', 'co', '-r10',
        local_repo(
            'svn+http://svn.colorstudy.com/INITools/trunk',
            tmpdir.join("cache"),
        ),
        'initools-trunk',
    )
    # Install with develop
    script.run(
        'python', 'setup.py', 'develop',
        cwd=script.scratch_path / 'initools-trunk',
        expect_stderr=True,
    )
    result = script.pip('freeze', expect_stderr=True)

    expected = textwrap.dedent("""\
        Script result: pip freeze
        -- stdout: --------------------
        ...-e %s@10#egg=INITools-0.3.1dev...-dev_r10
        ...""" % checkout_path)
    _check_output(result, expected)


def test_freeze_git_clone(script, tmpdir):
    """
    Test freezing a Git clone.
    """
    result = script.run(
        'git',
        'clone',
        local_repo(
            'git+http://github.com/pypa/pip-test-package.git',
            tmpdir.join("cache"),
        ),
        'pip-test-package',
        expect_stderr=True,
    )
    result = script.run(
        'git',
        'checkout',
        '7d654e66c8fa7149c165ddeffa5b56bc06619458',
        cwd=script.scratch_path / 'pip-test-package',
        expect_stderr=True,
    )
    result = script.run(
        'python', 'setup.py', 'develop',
        cwd=script.scratch_path / 'pip-test-package'
    )
    result = script.pip('freeze', expect_stderr=True)
    expected = textwrap.dedent(
        """
            Script result: ...pip freeze
            -- stdout: --------------------
            ...-e %s@...#egg=pip_test_package-...
            ...
        """ %
        local_checkout(
            'git+http://github.com/pypa/pip-test-package.git',
            tmpdir.join("cache"),
        )
    ).strip()
    _check_output(result, expected)

    result = script.pip(
        'freeze', '-f',
        '%s#egg=pip_test_package' %
        local_checkout(
            'git+http://github.com/pypa/pip-test-package.git',
            tmpdir.join("cache"),
        ),
        expect_stderr=True,
    )
    expected = textwrap.dedent(
        """
            Script result: pip freeze -f %(repo)s#egg=pip_test_package
            -- stdout: --------------------
            -f %(repo)s#egg=pip_test_package...
            -e %(repo)s@...#egg=pip_test_package-0.1.1
            ...
        """ %
        {
            'repo': local_checkout(
                'git+http://github.com/pypa/pip-test-package.git',
                tmpdir.join("cache"),
            ),
        },
    ).strip()
    _check_output(result, expected)


def test_freeze_mercurial_clone(script, tmpdir):
    """
    Test freezing a Mercurial clone.

    """
    result = script.run(
        'hg', 'clone',
        '-r', 'c9963c111e7c',
        local_repo(
            'hg+http://bitbucket.org/pypa/pip-test-package',
            tmpdir.join("cache"),
        ),
        'pip-test-package',
    )
    result = script.run(
        'python', 'setup.py', 'develop',
        cwd=script.scratch_path / 'pip-test-package',
        expect_stderr=True,
    )
    result = script.pip('freeze', expect_stderr=True)
    expected = textwrap.dedent(
        """
            Script result: ...pip freeze
            -- stdout: --------------------
            ...-e %s@...#egg=pip_test_package-...
            ...
        """ %
        local_checkout(
            'hg+http://bitbucket.org/pypa/pip-test-package',
            tmpdir.join("cache"),
        ),
    ).strip()
    _check_output(result, expected)

    result = script.pip(
        'freeze', '-f',
        '%s#egg=pip_test_package' %
        local_checkout(
            'hg+http://bitbucket.org/pypa/pip-test-package',
            tmpdir.join("cache"),
        ),
        expect_stderr=True,
    )
    expected = textwrap.dedent(
        """
            Script result: ...pip freeze -f %(repo)s#egg=pip_test_package
            -- stdout: --------------------
            -f %(repo)s#egg=pip_test_package
            ...-e %(repo)s@...#egg=pip_test_package-dev
            ...
        """ %
        {
            'repo': local_checkout(
                'hg+http://bitbucket.org/pypa/pip-test-package',
                tmpdir.join("cache"),
            ),
        },
    ).strip()
    _check_output(result, expected)


def test_freeze_bazaar_clone(script, tmpdir):
    """
    Test freezing a Bazaar clone.

    """

    checkout_path = local_checkout(
        'bzr+http://bazaar.launchpad.net/%7Edjango-wikiapp/django-wikiapp/'
        'release-0.1',
        tmpdir.join("cache"),
    )
    # bzr internally stores windows drives as uppercase; we'll match that.
    checkout_pathC = checkout_path.replace('c:', 'C:')

    result = script.run(
        'bzr', 'checkout', '-r', '174',
        local_repo(
            'bzr+http://bazaar.launchpad.net/%7Edjango-wikiapp/django-wikiapp/'
            'release-0.1',
            tmpdir.join("cache"),
        ),
        'django-wikiapp',
    )
    result = script.run(
        'python', 'setup.py', 'develop',
        cwd=script.scratch_path / 'django-wikiapp',
    )
    result = script.pip('freeze', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze
        -- stdout: --------------------
        ...-e %s@...#egg=django_wikiapp-...
        ...""" % checkout_pathC)
    _check_output(result, expected)

    result = script.pip(
        'freeze', '-f',
        '%s/#egg=django-wikiapp' % checkout_path,
        expect_stderr=True,
    )
    expected = textwrap.dedent("""\
        Script result: ...pip freeze -f %(repo)s/#egg=django-wikiapp
        -- stdout: --------------------
        -f %(repo)s/#egg=django-wikiapp
        ...-e %(repoC)s@...#egg=django_wikiapp-...
        ...""" % {'repoC': checkout_pathC, 'repo': checkout_path})
    _check_output(result, expected)


def test_freeze_with_local_option(script):
    """
    Test that wsgiref (from global site-packages) is reported normally, but not
    with --local.
    """
    result = script.pip('install', 'initools==0.2')
    result = script.pip('freeze', expect_stderr=True)
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

    result = script.pip('freeze', '--local', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze --local
        -- stdout: --------------------
        INITools==0.2
        <BLANKLINE>""")
    _check_output(result, expected)


def test_freeze_with_requirement_option(script):
    """
    Test that new requirements are created correctly with --requirement hints

    """
    ignores = textwrap.dedent("""\
        # Unchanged requirements below this line
        -r ignore.txt
        --requirement ignore.txt
        -Z ignore
        --always-unzip ignore
        -f http://ignore
        -i http://ignore
        --extra-index-url http://ignore
        --find-links http://ignore
        --index-url http://ignore
        """)
    script.scratch_path.join("hint.txt").write(textwrap.dedent("""\
        INITools==0.1
        NoExist==4.2
        """) + ignores)
    result = script.pip('install', 'initools==0.2')
    result = script.pip_install_local('simple')
    result = script.pip(
        'freeze', '--requirement', 'hint.txt',
        expect_stderr=True,
    )
    expected = """\
Script result: pip freeze --requirement hint.txt
-- stderr: --------------------
Requirement file contains NoExist==4.2, but that package is not installed

-- stdout: --------------------
INITools==0.2
""" + ignores + "## The following requirements were added by pip --freeze:..."
    _check_output(result, expected)
