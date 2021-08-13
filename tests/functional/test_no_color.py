"""
Test specific for the --no-color option
"""
import os
import subprocess

import pytest


def test_no_color(script):
    """Ensure colour output disabled when --no-color is passed."""
    # Using 'script' in this test allows for transparently testing pip's output
    # since pip is smart enough to disable colour output when piped, which is
    # not the behaviour we want to be testing here.
    #
    # On the other hand, this test is non-portable due to the options passed to
    # 'script' and well as the mere use of the same.
    #
    # This test will stay until someone has the time to rewrite it.
    command = (
        "script --flush --quiet --return /tmp/pip-test-no-color.txt "
        '--command "pip uninstall {} noSuchPackage"'
    )

    def get_run_output(option):
        cmd = command.format(option)
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        proc.communicate()
        if proc.returncode:
            pytest.skip("Unable to capture output using script: " + cmd)

        try:
            with open("/tmp/pip-test-no-color.txt") as output_file:
                retval = output_file.read()
            return retval
        finally:
            os.unlink("/tmp/pip-test-no-color.txt")

    assert "\x1b" in get_run_output(option=""), "Expected color in output"
    assert "\x1b" not in get_run_output(
        option="--no-color"
    ), "Expected no color in output"
