import os
import tempfile
from pip.baseparser import create_main_parser
from pip.basecommand import Command


class FakeCommand(Command):
    name = "fake"

    def run(self, options, args):
        # raise an error to trigger --log-file writing
        raise Exception("testing")


def test_should_accept_custom_log_location():
    """Test custom log location through --log
    """
    log_path = tempfile.mktemp()
    parser = create_main_parser()
    options, args = parser.parse_args(["fake", "--log", log_path])

    cmd = FakeCommand(parser)
    cmd.main(args, options)

    assert os.path.exists(log_path)
    os.remove(log_path)


def test_log_file_through_log_file_option_should_work():
    # there was a bug with regards to --log-file not being respected:
    # https://github.com/pypa/pip/issues/350
    log_file_path = tempfile.mktemp()
    parser = create_main_parser()
    options, args = parser.parse_args(["fake", "--log-file", log_file_path])

    cmd = FakeCommand(parser)
    cmd.main(args, options)

    assert os.path.exists(log_file_path)
    os.remove(log_file_path)

def test_log_and_log_file_options_should_work_well_together():
    log_path = tempfile.mktemp()
    log_file_path = tempfile.mktemp()
    parser = create_main_parser()
    options, args = parser.parse_args([
        "fake",
        "--log", log_path,
        "--log-file", log_file_path])

    cmd = FakeCommand(parser)
    cmd.main(args, options)

    assert os.path.exists(log_path)
    os.remove(log_path)
    assert os.path.exists(log_file_path)
    os.remove(log_file_path)
