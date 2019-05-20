import pytest
from mock import patch

from pip._internal.vcs.subversion import Subversion


@patch('pip._internal.vcs.subversion.Subversion.get_remote_call_options')
@patch('pip._internal.vcs.call_subprocess')
@pytest.mark.network
def test_obtain_should_recognize_auth_info_url(
        call_subprocess_mock, get_remote_call_options_mock, script):
    get_remote_call_options_mock.return_value = []
    url = 'svn+http://username:password@svn.example.com/'
    svn = Subversion()
    svn.obtain(script.scratch_path / 'test', url=url)
    assert call_subprocess_mock.call_args[0][0] == [
        svn.name, 'checkout', '-q', '--username', 'username', '--password',
        'password', 'http://svn.example.com/',
        script.scratch_path / 'test',
    ]


@patch('pip._internal.vcs.subversion.Subversion.get_remote_call_options')
@patch('pip._internal.vcs.call_subprocess')
@pytest.mark.network
def test_export_should_recognize_auth_info_url(
        call_subprocess_mock, get_remote_call_options_mock, script):
    get_remote_call_options_mock.return_value = []
    url = 'svn+http://username:password@svn.example.com/'
    svn = Subversion()
    svn.export(script.scratch_path / 'test', url=url)
    assert call_subprocess_mock.call_args[0][0] == [
        svn.name, 'export', '--username', 'username', '--password',
        'password', 'http://svn.example.com/',
        script.scratch_path / 'test',
    ]
