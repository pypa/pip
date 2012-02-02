from mock import patch
from pip.vcs.subversion import Subversion
from tests.test_pip import reset_env

@patch('pip.vcs.subversion.call_subprocess')
def test_obtain_should_recognize_auth_info_in_url(call_subprocess_mock):
    env = reset_env()
    svn = Subversion(url='svn+http://username:password@svn.example.com/')
    svn.obtain(env.scratch_path/'test')
    call_subprocess_mock.assert_called_with([
        svn.cmd, 'checkout', '-q', '--username', 'username', '--password', 'password',
        'http://username:password@svn.example.com/', env.scratch_path/'test'])

@patch('pip.vcs.subversion.call_subprocess')
def test_export_should_recognize_auth_info_in_url(call_subprocess_mock):
    env = reset_env()
    svn = Subversion(url='svn+http://username:password@svn.example.com/')
    svn.export(env.scratch_path/'test')
    assert call_subprocess_mock.call_args[0] == ([
        svn.cmd, 'export', '--username', 'username', '--password', 'password',
        'http://username:password@svn.example.com/', env.scratch_path/'test'],)
