import logging

from pip._internal.cli.base_command import Command
from pip._internal.utils.logging import BrokenStdoutLoggingError


class FakeCommand(Command):
    name = 'fake'
    summary = name

    def __init__(self, run_func=None, error=False):
        if error:
            def run_func():
                raise SystemExit(1)

        self.run_func = run_func
        super(FakeCommand, self).__init__()

    def main(self, args):
        args.append("--disable-pip-version-check")
        return super(FakeCommand, self).main(args)

    def run(self, options, args):
        logging.getLogger("pip.tests").info("fake")
        if self.run_func:
            return self.run_func()


class FakeCommandWithUnicode(FakeCommand):
    name = 'fake_unicode'
    summary = name

    def run(self, options, args):
        logging.getLogger("pip.tests").info(b"bytes here \xE9")
        logging.getLogger("pip.tests").info(
            b"unicode here \xC3\xA9".decode("utf-8")
        )


class TestCommand(object):

    def call_main(self, capsys, args):
        """
        Call command.main(), and return the command's stderr.
        """
        def raise_broken_stdout():
            raise BrokenStdoutLoggingError()

        cmd = FakeCommand(run_func=raise_broken_stdout)
        status = cmd.main(args)
        assert status == 1
        stderr = capsys.readouterr().err

        return stderr

    def test_raise_broken_stdout(self, capsys):
        """
        Test raising BrokenStdoutLoggingError.
        """
        stderr = self.call_main(capsys, [])

        assert stderr.rstrip() == 'ERROR: Pipe to stdout was broken'

    def test_raise_broken_stdout__debug_logging(self, capsys):
        """
        Test raising BrokenStdoutLoggingError with debug logging enabled.
        """
        stderr = self.call_main(capsys, ['-v'])

        assert 'ERROR: Pipe to stdout was broken' in stderr
        assert 'Traceback (most recent call last):' in stderr


class Test_base_command_logging(object):
    """
    Test `pip.base_command.Command` setting up logging consumers based on
    options
    """

    def test_log_command_success(self, tmpdir):
        """
        Test the --log option logs when command succeeds
        """
        cmd = FakeCommand()
        log_path = tmpdir.join('log')
        cmd.main(['fake', '--log', log_path])
        with open(log_path) as f:
            assert 'fake' == f.read().strip()[:4]

    def test_log_command_error(self, tmpdir):
        """
        Test the --log option logs when command fails
        """
        cmd = FakeCommand(error=True)
        log_path = tmpdir.join('log')
        cmd.main(['fake', '--log', log_path])
        with open(log_path) as f:
            assert 'fake' == f.read().strip()[:4]

    def test_log_file_command_error(self, tmpdir):
        """
        Test the --log-file option logs (when there's an error).
        """
        cmd = FakeCommand(error=True)
        log_file_path = tmpdir.join('log_file')
        cmd.main(['fake', '--log-file', log_file_path])
        with open(log_file_path) as f:
            assert 'fake' == f.read().strip()[:4]

    def test_unicode_messages(self, tmpdir):
        """
        Tests that logging bytestrings and unicode objects don't break logging
        """
        cmd = FakeCommandWithUnicode()
        log_path = tmpdir.join('log')
        cmd.main(['fake_unicode', '--log', log_path])
