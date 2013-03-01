import os
import tempfile
import textwrap
from tests.test_pip import reset_env, run_pip, clear_environ, write_file, path_to_url, here


def test_options_from_env_vars():
    """
    Test if ConfigOptionParser reads env vars (e.g. not using PyPI here)

    """
    environ = clear_environ(os.environ.copy())
    environ['PIP_NO_INDEX'] = '1'
    reset_env(environ)
    result = run_pip('install', '-vvv', 'INITools', expect_error=True)
    assert "Ignoring indexes:" in result.stdout, str(result)
    assert "DistributionNotFound: No distributions at all found for INITools" in result.stdout


def test_command_line_options_override_env_vars():
    """
    Test that command line options override environmental variables.

    """
    environ = clear_environ(os.environ.copy())
    environ['PIP_INDEX_URL'] = 'http://b.pypi.python.org/simple/'
    reset_env(environ)
    result = run_pip('install', '-vvv', 'INITools', expect_error=True)
    assert "Getting page http://b.pypi.python.org/simple/INITools" in result.stdout
    reset_env(environ)
    result = run_pip('install', '-vvv', '--index-url', 'http://download.zope.org/ppix', 'INITools', expect_error=True)
    assert "b.pypi.python.org" not in result.stdout
    assert "Getting page http://download.zope.org/ppix" in result.stdout


def test_env_vars_override_config_file():
    """
    Test that environmental variables override settings in config files.

    """
    fd, config_file = tempfile.mkstemp('-pip.cfg', 'test-')
    try:
        _test_env_vars_override_config_file(config_file)
    finally:
        # `os.close` is a workaround for a bug in subprocess
        # http://bugs.python.org/issue3210
        os.close(fd)
        os.remove(config_file)


def _test_env_vars_override_config_file(config_file):
    environ = clear_environ(os.environ.copy())
    environ['PIP_CONFIG_FILE'] = config_file # set this to make pip load it
    reset_env(environ)
    # It's important that we test this particular config value ('no-index')
    # because their is/was a bug which only shows up in cases in which
    # 'config-item' and 'config_item' hash to the same value modulo the size
    # of the config dictionary.
    write_file(config_file, textwrap.dedent("""\
        [global]
        no-index = 1
        """))
    result = run_pip('install', '-vvv', 'INITools', expect_error=True)
    assert "DistributionNotFound: No distributions at all found for INITools" in result.stdout
    environ['PIP_NO_INDEX'] = '0'
    reset_env(environ)
    result = run_pip('install', '-vvv', 'INITools', expect_error=True)
    assert "Successfully installed INITools" in result.stdout


def test_command_line_append_flags():
    """
    Test command line flags that append to defaults set by environmental variables.

    """
    environ = clear_environ(os.environ.copy())
    environ['PIP_FIND_LINKS'] = 'http://pypi.pinaxproject.com'
    reset_env(environ)
    result = run_pip('install', '-vvv', 'INITools', expect_error=True)
    assert "Analyzing links from page http://pypi.pinaxproject.com" in result.stdout
    reset_env(environ)
    find_links = path_to_url(os.path.join(here, 'packages'))
    result = run_pip('install', '-vvv', '--find-links', find_links, 'INITools', expect_error=True)
    assert "Analyzing links from page http://pypi.pinaxproject.com" in result.stdout
    assert "Skipping link %s" % find_links in result.stdout


def test_command_line_appends_correctly():
    """
    Test multiple appending options set by environmental variables.

    """
    environ = clear_environ(os.environ.copy())
    find_links = path_to_url(os.path.join(here, 'packages'))
    environ['PIP_FIND_LINKS'] = 'http://pypi.pinaxproject.com %s' % find_links
    reset_env(environ)
    result = run_pip('install', '-vvv', 'INITools', expect_error=True)

    assert "Analyzing links from page http://pypi.pinaxproject.com" in result.stdout, result.stdout
    assert "Skipping link %s" % find_links in result.stdout


def test_config_file_override_stack():
    """
    Test config files (global, overriding a global config with a
    local, overriding all with a command line flag).

    """
    fd, config_file = tempfile.mkstemp('-pip.cfg', 'test-')
    try:
        _test_config_file_override_stack(config_file)
    finally:
        # `os.close` is a workaround for a bug in subprocess
        # http://bugs.python.org/issue3210
        os.close(fd)
        os.remove(config_file)


def _test_config_file_override_stack(config_file):
    environ = clear_environ(os.environ.copy())
    environ['PIP_CONFIG_FILE'] = config_file # set this to make pip load it
    reset_env(environ)
    write_file(config_file, textwrap.dedent("""\
        [global]
        index-url = http://download.zope.org/ppix
        """))
    result = run_pip('install', '-vvv', 'INITools', expect_error=True)
    assert "Getting page http://download.zope.org/ppix/INITools" in result.stdout
    reset_env(environ)
    write_file(config_file, textwrap.dedent("""\
        [global]
        index-url = http://download.zope.org/ppix
        [install]
        index-url = http://pypi.appspot.com/
        """))
    result = run_pip('install', '-vvv', 'INITools', expect_error=True)
    assert "Getting page http://pypi.appspot.com/INITools" in result.stdout
    result = run_pip('install', '-vvv', '--index-url', 'http://pypi.python.org/simple', 'INITools', expect_error=True)
    assert "Getting page http://download.zope.org/ppix/INITools" not in result.stdout
    assert "Getting page http://pypi.appspot.com/INITools" not in result.stdout
    assert "Getting page http://pypi.python.org/simple/INITools" in result.stdout


def test_log_file_no_directory():
    """
    Test opening a log file with no directory name.

    """
    from pip.basecommand import open_logfile
    fp = open_logfile('testpip.log')
    fp.write('can write')
    fp.close()
    assert os.path.exists(fp.name)
    os.remove(fp.name)


def test_get_config_files():
    """
    Test the loading of local config files

    """
    from pip.baseparser import ConfigOptionParser
    from pip.locations import default_config_file, default_config_file_name
    parser = ConfigOptionParser(name = "test")
    local_config_path = os.path.abspath(default_config_file_name)
    fp = None
    if not os.path.exists(default_config_file_name):
        fp = open(default_config_file_name, "w")
    files = parser.get_config_files()
    if fp:
        fp.close()
        os.remove(fp.name)
    assert [default_config_file, local_config_path] == files


def test_multiple_configs():
    """
    Test the support of multiple config files, and the config files precedence 

    """
    fd1, config_file1 = tempfile.mkstemp('-pip.cfg', 'test1-')
    fd2, config_file2 = tempfile.mkstemp('-pip.cfg', 'test1-')
    try:
        _test_multiple_configs(config_file1, config_file2)
    finally:
        os.close(fd1)
        os.remove(config_file1)
        os.close(fd2)
        os.remove(config_file2)


def _test_multiple_configs(config1, config2):
    """
    Test the ability to have multiple config files override each other

    """
    from pip.baseparser import ConfigOptionParser
    write_file(config1, textwrap.dedent("""\
        [global]
        no-index = 1
        index-url = http://download.zope.org/ppix
        """))
    write_file(config2, textwrap.dedent("""\
        [global]
        no-index = 0
        """))
    parser = ConfigOptionParser(name="test")
    parser.read_config_files([config1, config2])
    no_index = parser.config.get("global", "no-index")
    index_url = parser.config.get("global", "index-url")
    assert "0" == no_index
    assert "http://download.zope.org/ppix" == index_url


def test_substitute_config_value():
    """
    Test the config placeholders and their substitutions

    """
    from pip.baseparser import ConfigOptionParser
    parser = ConfigOptionParser(name="test")
    file_ = os.path.abspath("pip.ini")
    assert "".join(["--",file_,"--"]) == parser.substitute_config_value("--%(file)s--", file_)
    assert "".join(["--", os.path.dirname(file_), "--"]) == parser.substitute_config_value("--%(here)s--", file_)
    assert "".join(["--",os.getcwd(),"--"]) == parser.substitute_config_value("--%(cwd)s--", file_)


def test_update_sys_path():
    """
    Test the directive for appending paths to the sys.path

    """
    import sys
    old_paths = list(sys.path)
    fd, config_file = tempfile.mkstemp('-pip.cfg', 'test-')
    path = tempfile.mkdtemp('-pip', 'test-')
    try:
        _test_update_sys_path(config_file, path)
    finally:
        sys.path = old_paths
        os.close(fd)
        os.remove(config_file)
        os.rmdir(path)


def _test_update_sys_path(config_file, path):
    import sys
    from pip.baseparser import ConfigOptionParser
    config = """\
        [global]
        sys.path = %s
        """ % path 
    write_file(config_file, textwrap.dedent(config))
    parser = ConfigOptionParser(name="test")
    assert path not in sys.path
    parser.read_config_files([config_file])
    parser.update_sys_path()
    assert path in sys.path
