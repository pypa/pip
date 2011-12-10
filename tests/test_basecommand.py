from pip.basecommand import Command

def test_timeout_properly_passed_on():
    """
    Check that the --timeout parameter gets properly passed on to the socket 
    (special no regression test #70)
    """
    class TestCommand(Command):
        name = "test-cmd"
    cmd = TestCommand()    
    complete_args = ['install', '--timeout', '1', 'traits']
    args = ['--timeout', '1', 'traits']
    import optparse
    initial_options = {'log': None, 'timeout': 15, 'venv': None, 'no_input': False, 'help': None, 'venv_base': '/Users/ogirardot/Documents/Python/virtualenv', 'site_packages': None, 'quiet': 0, 'default_vcs': '', 'require_venv': False, 'proxy': '', 'respect_venv': 1, 'skip_requirements_regex': '', 'log_file': '/Users/ogirardot/.pip/pip.log', 'log_explicit_levels': False, 'verbose': 0}
    cmd.main(complete_args, args, optparse.Values(initial_options))
    import socket
    assert socket.getdefaulttimeout() == 1
                                               