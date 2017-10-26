"""
Test specific for the --no-color option
"""
import os
import platform
import subprocess as sp

import pytest


@pytest.mark.skipif(platform.system() == 'Windows',
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
        output = result.read()

    os.unlink("/tmp/colored-output.txt")

    assert output.startswith("\x1b[31m")
    assert output.endswith("\x1b[0m\n")

    sp.Popen("script --flush --quiet --return /tmp/no-color-output.txt"
             " --command \"pip --no-color uninstall noSuchPackage\"",
             shell=True,
             stdout=sp.PIPE, stderr=sp.PIPE).communicate()

    with open("/tmp/no-color-output.txt", "r") as result:
        output = result.read()

    os.unlink("/tmp/no-color-output.txt")

    assert not output.startswith("\x1b[31m")
    assert not output.endswith("\x1b[0m\n")
