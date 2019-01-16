import logging
import re

from pip._internal.cli.base_command import Command


class FakeCommand(Command):
    name = 'fake'
    summary = name

    def __init__(self, error=False):
        self.error = error
        super(FakeCommand, self).__init__()

    def main(self, args):
        args.append("--disable-pip-version-check")
        return super(FakeCommand, self).main(args)

    def run(self, options, args):
        logging.getLogger("pip.tests").info("fake")
        if self.error:
            raise SystemExit(1)


class FakeCommandWithUnicode(FakeCommand):
    name = 'fake_unicode'
    summary = name

    def run(self, options, args):
        logging.getLogger("pip.tests").info(b"bytes here \xE9")
        logging.getLogger("pip.tests").info(
            b"unicode here \xC3\xA9".decode("utf-8")
        )


class Test_base_command_logging(object):
    """
    Test `pip.base_command.Command` setting up logging consumers based on
    options
    """

    def _remove_timestamp(self, l):
        timestamp_prefix_length = len('2019-01-16T22:00:37 ')
        return l[timestamp_prefix_length:]

    def test_log_command_success(self, tmpdir):
        """
        Test the --log option logs when command succeeds
        """
        cmd = FakeCommand()
        log_path = tmpdir.join('log')
        cmd.main(['fake', '--log', log_path])
        with open(log_path) as f:
            assert 'fake' == self._remove_timestamp(f.read().strip())[:4]

    def test_log_command_error(self, tmpdir):
        """
        Test the --log option logs when command fails
        """
        cmd = FakeCommand(error=True)
        log_path = tmpdir.join('log')
        cmd.main(['fake', '--log', log_path])
        with open(log_path) as f:
            assert 'fake' == self._remove_timestamp(f.read().strip())[:4]

    def test_log_file_command_error(self, tmpdir):
        """
        Test the --log-file option logs (when there's an error).
        """
        cmd = FakeCommand(error=True)
        log_file_path = tmpdir.join('log_file')
        cmd.main(['fake', '--log-file', log_file_path])
        with open(log_file_path) as f:
            assert 'fake' == self._remove_timestamp(f.read().strip())[:4]

    def test_log_command_is_timestamped(self, tmpdir):
        """
        Test the --log option logs a timestamp
        """
        cmd = FakeCommand()
        log_path = tmpdir.join('log')
        cmd.main(['fake', '--log', log_path])
        with open(log_path) as f:
            assert re.match('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2} ',
                            f.read().strip())

    def test_unicode_messages(self, tmpdir):
        """
        Tests that logging bytestrings and unicode objects don't break logging
        """
        cmd = FakeCommandWithUnicode()
        log_path = tmpdir.join('log')
        cmd.main(['fake_unicode', '--log', log_path])
