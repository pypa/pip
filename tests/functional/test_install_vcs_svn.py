from mock import patch

from pip._internal.vcs import RevOptions
from pip._internal.vcs.subversion import Subversion


@patch('pip._internal.vcs.call_subprocess')
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


@patch('pip._internal.vcs.call_subprocess')
def test_fetch_new_should_include_remote_call_options(
        call_subprocess_mock, script):
    url = 'svn+http://username:password@svn.example.com/'
    # use_interactive is set to False to test that remote call options are
    # properly added.
    svn = Subversion(use_interactive=False)
    rev_options = RevOptions(Subversion)
    dest = script.scratch_path / 'test'
    svn.fetch_new(dest, url, rev_options)
    assert call_subprocess_mock.call_args[0][0] == [
        svn.name, 'checkout', '-q', '--non-interactive', url, dest,
    ]


@patch('pip._internal.vcs.call_subprocess')
def test_switch_should_include_remote_call_options(
        call_subprocess_mock, script):
    url = 'svn+http://username:password@svn.example.com/'
    # use_interactive is set to False to test that remote call options are
    # properly added.
    svn = Subversion(use_interactive=False)
    rev_options = RevOptions(Subversion)
    dest = script.scratch_path / 'test'
    svn.switch(dest, url, rev_options)
    assert call_subprocess_mock.call_args[0][0] == [
        svn.name, 'switch', '--non-interactive', url, dest,
    ]


@patch('pip._internal.vcs.call_subprocess')
def test_update_should_include_remote_call_options(
        call_subprocess_mock, script):
    url = 'svn+http://username:password@svn.example.com/'
    # use_interactive is set to False to test that remote call options are
    # properly added.
    svn = Subversion(use_interactive=False)
    rev_options = RevOptions(Subversion)
    dest = script.scratch_path / 'test'
    svn.update(dest, url, rev_options)
    assert call_subprocess_mock.call_args[0][0] == [
        svn.name, 'update', '--non-interactive', dest,
    ]
