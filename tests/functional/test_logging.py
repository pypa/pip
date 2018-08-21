"""
Test specific for the --no-color option
"""
import os
import subprocess as sbp

import pytest
from pip._vendor.six import PY2


@pytest.mark.usefixtures('script')
def test_no_color():
    """Ensure colour output disabled when --no-color is passed.
    """
    # Using 'script' in this test allows for transparently testing pip's output
    # since pip is smart enough to disable colour output when piped, which is
    # not the behaviour we want to be testing here.
    #
    # On the other hand, this test is non-portable due to the options passed to
    # 'script' and well as the mere use of the same.
    #
    # This test will stay until someone has the time to rewrite it.
    command = (
        'script --flush --quiet --return /tmp/pip-test-no-color.txt '
        '--command "pip uninstall {} noSuchPackage"'
    )

    def get_run_output(option):
        cmd = command.format(option)
        proc = sbp.Popen(
            cmd, shell=True, stdout=sbp.PIPE, stderr=sbp.PIPE,
        )
        proc.communicate()
        if proc.returncode:
            pytest.skip("Unable to capture output using script: " + cmd)

        try:
            with open("/tmp/pip-test-no-color.txt", "r") as output_file:
                retval = output_file.read()
            return retval
        finally:
            os.unlink("/tmp/pip-test-no-color.txt")

    assert "\x1b" in get_run_output(option=""), "Expected color in output"
    assert "\x1b" not in get_run_output(option="--no-color"), \
        "Expected no color in output"


def test_broken_pipe_output(script):
    """Ensure `freeze` stops if its stdout stream is broken."""
    from . import test_freeze

    # Install some packages for freeze to print something.
    test_freeze.test_basic_freeze(script)

    # `freeze` cmd writes stdout in a loop, so a broken-pipe-error
    #  breaks immediately with the 2 lines above, as expected.
    cmd = 'pip freeze | head -n2'

    stderr = sbp.check_output(cmd, stderr=sbp.PIPE, shell=True)
    assert not stderr, stderr.decode()


def test_broken_pipe_logger():
    """Ensure logs stop if their stream is broken."""
    # `download` cmd has a lot of log-statements.
    cmd = 'pip -v download nobody| head -n2'

    stderr = sbp.check_output(cmd, stderr=sbp.PIPE, shell=True)
    # When breaks the stream that the logging is writing into,
    # in PY3 these 2 lines are emitted in stderr:
    #    Exception ignored in: <_io.TextIOWrapper name='<stdout>' mode='w' ...
    #    BrokenPipeError: [Errno 32] Broken pipe\n"
    #
    # Before #5721, pip did not stop the 1st time, but it continued
    # printing them lines on each `stream.flush()`!
    if PY2:
        assert not stderr, stderr
    else:
        assert stderr.count(b'\n') == 2, stderr.decode()
        assert b'Exception ignored in' in stderr, stderr.decode()
