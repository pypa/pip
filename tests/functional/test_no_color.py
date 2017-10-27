"""
Test specific for the --no-color option
"""
import os
import platform
import subprocess as sp
import sys

import pytest


@pytest.mark.skipif(sys.platform == 'win32',
                    reason="does not run on windows")
def test_no_color(script):

    """
    Test uninstalling an existing package - should out put red error

    We must use subprocess with the script command, since redirection
    in unix platform causes text coloring to disapper. Thus, we can't
    use the testing infrastructure that other options has.
    """

    sp.Popen("script --flush --quiet --return /tmp/colored-output.txt"
             " --command \"pip uninstall noSuchPackage\"", shell=True,
             stdout=sp.PIPE, stderr=sp.PIPE).communicate()

    with open("/tmp/colored-output.txt", "r") as result:

        red_lines = 0
        reset_lines = 0

        for line in result.readlines():
            if line.startswith("\x1b[31m"):
                red_lines += 1
            if line.endswith("\x1b[0m\n"):
                reset_lines += 1

        assert red_lines >= 1
        assert reset_lines >= 1

    os.unlink("/tmp/colored-output.txt")

    sp.Popen("script --flush --quiet --return /tmp/no-color-output.txt"
             " --command \"pip --no-color uninstall noSuchPackage\"",
             shell=True,
             stdout=sp.PIPE, stderr=sp.PIPE).communicate()

    with open("/tmp/no-color-output.txt", "r") as result:
        red_lines = 0
        reset_lines = 0
        for line in result.readlines():
            if line.startswith("\x1b[31m"):
                red_lines += 1
            if line.endswith("\x1b[0m\n"):
                reset_lines += 1

    os.unlink("/tmp/no-color-output.txt")

    assert red_lines == 0
    assert reset_lines == 0
