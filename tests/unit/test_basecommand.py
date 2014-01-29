import os
from pip.basecommand import Command
from pip.log import logger


class FakeCommand(Command):
    name = 'fake'
    summary = name

    def __init__(self, error=False):
        self.error = error
        super(FakeCommand, self).__init__()

    def run(self, options, args):
        logger.info("fake")
        if self.error:
            raise SystemExit(1)


class Test_basecommand_logging(object):
    """
    Test `pip.basecommand.Command` setting up logging consumers based on
    options
    """

    def teardown(self):
        logger.consumers = []

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

    def test_log_file_command_success(self, tmpdir):
        """
        Test the --log-file option *doesn't* log when command succeeds.
        (It's just the historical behavior? this just confirms it)
        """
        cmd = FakeCommand()
        log_file_path = tmpdir.join('log_file')
        cmd.main(['fake', '--log-file', log_file_path])
        assert not os.path.exists(log_file_path)

    def test_log_file_command_error(self, tmpdir):
        """
        Test the --log-file option logs (when there's an error).
        """
        cmd = FakeCommand(error=True)
        log_file_path = tmpdir.join('log_file')
        cmd.main(['fake', '--log-file', log_file_path])
        assert 'fake' == open(log_file_path).read().strip()[:4]

    def test_log_log_file(self, tmpdir):
        """
        Test the --log and --log-file options log together (when there's an
        error).
        """
        cmd = FakeCommand(error=True)
        log_path = tmpdir.join('log')
        log_file_path = tmpdir.join('log_file')
        cmd.main(['fake', '--log', log_path, '--log-file', log_file_path])
        assert 'fake' == open(log_path).read().strip()[:4]
        assert 'fake' == open(log_file_path).read().strip()[:4]

    def test_verbose_quiet(self):
        """
        Test additive quality of -v and -q
        """
        cmd = FakeCommand()
        cmd.main(['fake', '-vqq'])
        console_level = logger.consumers[0][0]
        assert console_level == logger.WARN
