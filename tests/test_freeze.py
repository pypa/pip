
import os
import textwrap
from doctest import OutputChecker, ELLIPSIS
from test_pip import  reset_env, run_pip, pyversion,  write_file, get_env


def test_freeze():
    """
    Some tests of freeze, first we have to install some stuff.  Note that
    the test is a little crude at the end because Python 2.5+ adds egg
    info to the standard library, so stuff like wsgiref will show up in
    the freezing.  (Probably that should be accounted for in pip, but
    currently it is not).

    TODO: refactor this test into multiple tests? (and maybe different
    test style instead of using doctest output checker)
    
    """
    env = reset_env()
    checker = OutputChecker()
    write_file('initools-req.txt', textwrap.dedent("""\
        INITools==0.2
        # and something else to test out:
        simplejson<=1.7.4
        """))
    result = run_pip('install', '-r', env.scratch_path/'initools-req.txt')
    result = run_pip('freeze', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: pip freeze
        -- stdout: --------------------
        INITools==0.2
        simplejson==1.7.4...
        <BLANKLINE>""")
    assert checker.check_output(expected, str(result), ELLIPSIS), result

    # Now lets try it with an svn checkout::
    result = env.run('svn', 'co', '-r3472', 'http://svn.colorstudy.com/INITools/trunk', 'initools-trunk')
    result = env.run('python', 'setup.py', 'develop',
            cwd=env.scratch_path/ 'initools-trunk')
    result = run_pip('freeze', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze
        -- stdout: --------------------
        -e svn+http://svn.colorstudy.com/INITools/trunk@3472#egg=INITools-0.2.1dev_r3472-py2...-dev_r3472
        simplejson==1.7.4...
        <BLANKLINE>""")
    assert checker.check_output(expected, str(result), ELLIPSIS), result

    # Now, straight from trunk (but not editable/setup.py develop)::
    result = env.run('easy_install', 'http://svn.colorstudy.com/INITools/trunk')
    result = run_pip('freeze', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze
        -- stderr: --------------------
        Warning: cannot find svn location for INITools==...dev-r...
        <BLANKLINE>
        -- stdout: --------------------
        ## FIXME: could not find svn URL in dependency_links for this package:
        INITools==...dev-r...
        simplejson==1.7.4...
        <BLANKLINE>""")
    assert checker.check_output(expected, str(result), ELLIPSIS), result

    # Bah, that's no good!  Let's give it a hint::
    result = run_pip('freeze', '-f', 'http://svn.colorstudy.com/INITools/trunk#egg=INITools-dev', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze -f http://svn.colorstudy.com/INITools/trunk#egg=INITools-dev
        -- stdout: --------------------
        -f http://svn.colorstudy.com/INITools/trunk#egg=INITools-dev
        # Installing as editable to satisfy requirement INITools==...dev-r...:
        -e svn+http://svn.colorstudy.com/INITools/trunk@...#egg=INITools-...dev_r...
        simplejson==1.7.4...
        <BLANKLINE>""")
    assert checker.check_output(expected, str(result), ELLIPSIS), result

def test_freeze_git_clone():
    """
    Test freezing a Git clone.
    
    """
    env = reset_env()
    checker = OutputChecker()
    result = env.run('git', 'clone', 'git://github.com/jezdez/django-pagination.git', 'django-pagination')
    result = env.run('git', 'checkout', '1df6507872d73ee387eb375428eafbfc253dfcd8',
            cwd= env.scratch_path/ 'django-pagination', expect_stderr=True)
    result = env.run('python', 'setup.py', 'develop',
            cwd=env.scratch_path / 'django-pagination')
    result = run_pip('freeze', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze
        -- stdout: --------------------
        -e git://github.com/jezdez/django-pagination.git@...#egg=django_pagination-...
        ...""")
    assert checker.check_output(expected, str(result), ELLIPSIS), result

    result = run_pip('freeze', '-f', 'git://github.com/jezdez/django-pagination.git#egg=django_pagination', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: pip freeze -f git://github.com/jezdez/django-pagination.git#egg=django_pagination
        -- stdout: --------------------
        -f git://github.com/jezdez/django-pagination.git#egg=django_pagination
        -e git://github.com/jezdez/django-pagination.git@...#egg=django_pagination-...-dev
        ...""")
    assert checker.check_output(expected, str(result), ELLIPSIS), result

def test_freeze_mercurial_clone():
    """
    Test freezing a Mercurial clone.
    
    """
    reset_env()
    env = get_env()
    checker = OutputChecker()
    result = env.run('hg', 'clone', '-r', 'f8f7eaf275c5', 'http://bitbucket.org/jezdez/django-dbtemplates/', 'django-dbtemplates')
    result = env.run('python', 'setup.py', 'develop',
            cwd=env.scratch_path/'django-dbtemplates')
    result = run_pip('freeze', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze
        -- stdout: --------------------
        -e hg+http://bitbucket.org/jezdez/django-dbtemplates/@...#egg=django_dbtemplates-...
        ...""")
    assert checker.check_output(expected, str(result), ELLIPSIS), result

    result = run_pip('freeze', '-f', 'hg+http://bitbucket.org/jezdez/django-dbtemplates#egg=django_dbtemplates', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze -f hg+http://bitbucket.org/jezdez/django-dbtemplates#egg=django_dbtemplates
        -- stdout: --------------------
        -f hg+http://bitbucket.org/jezdez/django-dbtemplates#egg=django_dbtemplates
        -e hg+http://bitbucket.org/jezdez/django-dbtemplates/@...#egg=django_dbtemplates-...
        ...""")
    assert checker.check_output(expected, str(result), ELLIPSIS), result

def test_freeze_bazaar_clone():
    """
    Test freezing a Bazaar clone.
    
    """
    reset_env()
    env = get_env()
    checker = OutputChecker()
    result = env.run('bzr', 'checkout', '-r', '174', 'http://bazaar.launchpad.net/%7Edjango-wikiapp/django-wikiapp/release-0.1/', 'django-wikiapp')
    result = env.run(os.path.join(env.bin_dir, 'python'), 'setup.py', 'develop',
            cwd=env.scratch_path/'django-wikiapp')
    result = run_pip('freeze', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze
        -- stdout: --------------------
        -e bzr+http://bazaar.launchpad.net/...django-wikiapp/django-wikiapp/release-0.1/@...#egg=django_wikiapp-...
        ...""")
    assert checker.check_output(expected, str(result), ELLIPSIS), result

    result = run_pip('freeze', '-f', 'bzr+http://bazaar.launchpad.net/%7Edjango-wikiapp/django-wikiapp/release-0.1/#egg=django-wikiapp', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze -f bzr+http://bazaar.launchpad.net/%7Edjango-wikiapp/django-wikiapp/release-0.1/#egg=django-wikiapp
        -- stdout: --------------------
        -f bzr+http://bazaar.launchpad.net/...django-wikiapp/django-wikiapp/release-0.1/#egg=django-wikiapp
        -e bzr+http://bazaar.launchpad.net/...django-wikiapp/django-wikiapp/release-0.1/@...#egg=django_wikiapp-...
        ...""")
    assert checker.check_output(expected, str(result), ELLIPSIS), result

def test_freeze_with_local_option():
    """
    Test that wsgiref (from global site-packages) is reported normally, but not with --local.
    
    """
    reset_env()
    checker = OutputChecker()
    result = run_pip('install', 'initools==0.2')
    result = run_pip('freeze', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze
        -- stdout: --------------------
        INITools==0.2
        wsgiref==...
        <BLANKLINE>""")
    assert checker.check_output(expected, str(result), ELLIPSIS), result

    result = run_pip('freeze', '--local', expect_stderr=True)
    expected = textwrap.dedent("""\
        Script result: ...pip freeze --local
        -- stdout: --------------------
        INITools==0.2
        <BLANKLINE>""")
    assert checker.check_output(expected, str(result), ELLIPSIS), result
