from unittest import TestCase

from mock import patch

from pip._internal.vcs import RevOptions
from pip._internal.vcs.subversion import Subversion


class TestSubversionArgs(TestCase):
    def setUp(self):
        patcher = patch('pip._internal.vcs.call_subprocess')
        self.addCleanup(patcher.stop)
        self.call_subprocess_mock = patcher.start()

        # Test Data.
        self.url = 'svn+http://username:password@svn.example.com/'
        # use_interactive is set to False to test that remote call options are
        # properly added.
        self.svn = Subversion(use_interactive=False)
        self.rev_options = RevOptions(Subversion)
        self.dest = '/tmp/test'

    def assert_call_args(self, args):
        assert self.call_subprocess_mock.call_args[0][0] == args

    def test_obtain(self):
        self.svn.obtain(self.dest, self.url)
        self.assert_call_args(
            ['svn', 'checkout', '-q', '--non-interactive', '--username',
             'username', '--password', 'password',
             'http://svn.example.com/', '/tmp/test'])

    def test_export(self):
        self.svn.export(self.dest, self.url)
        self.assert_call_args(
            ['svn', 'export', '--non-interactive', '--username', 'username',
             '--password', 'password', 'http://svn.example.com/',
             '/tmp/test'])

    def test_fetch_new(self):
        self.svn.fetch_new(self.dest, self.url, self.rev_options)
        self.assert_call_args(
            ['svn', 'checkout', '-q', '--non-interactive',
             'svn+http://username:password@svn.example.com/',
             '/tmp/test'])

    def test_fetch_new_revision(self):
        rev_options = RevOptions(Subversion, '123')
        self.svn.fetch_new(self.dest, self.url, rev_options)
        self.assert_call_args(
            ['svn', 'checkout', '-q', '--non-interactive',
             '-r', '123',
             'svn+http://username:password@svn.example.com/',
             '/tmp/test'])

    def test_switch(self):
        self.svn.switch(self.dest, self.url, self.rev_options)
        self.assert_call_args(
            ['svn', 'switch', '--non-interactive',
             'svn+http://username:password@svn.example.com/',
             '/tmp/test'])

    def test_update(self):
        self.svn.update(self.dest, self.url, self.rev_options)
        self.assert_call_args(
            ['svn', 'update', '--non-interactive', '/tmp/test'])
