import logging

from pip.basecommand import Command


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


class Test_basecommand_logging(object):
    """
    Test `pip.basecommand.Command` setting up logging consumers based on
    options
    """

    def test_log_command_success(self, tmpdir):
        """
        Test the --log option logs when command succeeds
        """
        cmd = FakeCommand()
        log_path = tmpdir.join('log')
        cmd.main(['fake', '--log', log_path])
        assert 'fake' == open(log_path).read().strip()[:4]

    def test_log_command_error(self, tmpdir):
        """
        Test the --log option logs when command fails
        """
        cmd = FakeCommand(error=True)
        log_path = tmpdir.join('log')
        cmd.main(['fake', '--log', log_path])
        assert 'fake' == open(log_path).read().strip()[:4]

    def test_log_file_command_error(self, tmpdir):
        """
        Test the --log-file option logs (when there's an error).
        """
        cmd = FakeCommand(error=True)
        log_file_path = tmpdir.join('log_file')
        cmd.main(['fake', '--log-file', log_file_path])
        assert 'fake' == open(log_file_path).read().strip()[:4]

    def test_unicode_messages(self, tmpdir):
        """
        Tests that logging bytestrings and unicode objects don't break logging
        """
        cmd = FakeCommandWithUnicode()
        log_path = tmpdir.join('log')
        cmd.main(['fake_unicode', '--log', log_path])
