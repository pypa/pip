import os
import shutil
import tempfile
from pip.basecommand import Command
from pip import main
from pip.commands import commands
from pip.log import logger


class FakeCommand(Command):
    name = 'fake'
    summary = name
    def __init__(self, main_parser):
        super(FakeCommand, self).__init__(main_parser)
    def run(self, options, args):
        logger.info("fake")

class FakeErrorCommand(Command):
    name = 'fake_error'
    summary = name
    def __init__(self, main_parser):
        super(FakeErrorCommand, self).__init__(main_parser)
    def run(self, options, args):
        logger.info("fake")
        raise SystemExit(1)


class Test_basecommand_logging(object):
    """
    Test `pip.basecommand.Command` setting up logging consumers based on options
    """

    def setup(self):
        self.tmpdir = tempfile.mkdtemp()
        commands[FakeCommand.name] = FakeCommand
        commands[FakeErrorCommand.name] = FakeErrorCommand

    def teardown(self):
        logger.consumers = []
        commands.pop(FakeErrorCommand.name)
        commands.pop(FakeCommand.name)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_log(self):
        """
        Test the --log option logs.
        """
        log_path = os.path.join(self.tmpdir, 'log')
        main(['fake', '--log', log_path])
        assert 'fake' == open(log_path).read().strip()[:4]

    def test_log_file_success(self):
        """
        Test the --log-file option *doesn't* log when command succeeds.
        (It's just the historical behavior? this just confirms it)
        """
        log_file_path = os.path.join(self.tmpdir, 'log_file')
        main(['fake', '--log-file', log_file_path])
        assert not os.path.exists(log_file_path)

    def test_log_file_error(self):
        """
        Test the --log-file option logs (when there's an error).
        """
        log_file_path = os.path.join(self.tmpdir, 'log_file')
        try:
            main(['fake_error', '--log-file', log_file_path])
        except SystemExit:
            assert 'fake' == open(log_file_path).read().strip()[:4]

    def test_log_log_file(self):
        """
        Test the --log and --log-file options log together (when there's an error).
        """
        log_path = os.path.join(self.tmpdir, 'log')
        log_file_path = os.path.join(self.tmpdir, 'log_file')
        try:
            main(['fake_error', '--log', log_path, '--log-file', log_file_path])
        except SystemExit:
            assert 'fake' == open(log_path).read().strip()[:4]
            assert 'fake' == open(log_file_path).read().strip()[:4]
