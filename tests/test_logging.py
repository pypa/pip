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
