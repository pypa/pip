import pytest
from mock import patch

from pip._internal.vcs.subversion import Subversion


@patch('pip._internal.vcs.call_subprocess')
@pytest.mark.network
def test_obtain_should_recognize_auth_info_url(call_subprocess_mock, script):
    url = 'svn+http://username:password@svn.example.com/'
    # use_interactive is set to False to test that remote call options are
    # properly added.
    svn = Subversion(use_interactive=False)
    svn.obtain(script.scratch_path / 'test', url=url)
    assert call_subprocess_mock.call_args[0][0] == [
        svn.name, 'checkout', '-q', '--non-interactive', '--username',
        'username', '--password', 'password', 'http://svn.example.com/',
        script.scratch_path / 'test',
    ]


@patch('pip._internal.vcs.call_subprocess')
@pytest.mark.network
def test_export_should_recognize_auth_info_url(call_subprocess_mock, script):
    url = 'svn+http://username:password@svn.example.com/'
    # use_interactive is set to False to test that remote call options are
    # properly added.
    svn = Subversion(use_interactive=False)
    svn.export(script.scratch_path / 'test', url=url)
    assert call_subprocess_mock.call_args[0][0] == [
        svn.name, 'export', '--non-interactive', '--username', 'username',
        '--password', 'password', 'http://svn.example.com/',
        script.scratch_path / 'test',
    ]
