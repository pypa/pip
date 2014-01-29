"""Test the test support."""
from __future__ import absolute_import

import filecmp
import re
from os.path import join, isdir

from tests.lib import SRC_DIR


def test_tmp_dir_exists_in_env(script):
    """
    Test that $TMPDIR == env.temp_path and path exists and env.assert_no_temp()
    passes (in fast env)
    """
    # need these tests to ensure the assert_no_temp feature of scripttest is
    # working
    script.assert_no_temp()  # this fails if env.tmp_path doesn't exist
    assert script.environ['TMPDIR'] == script.temp_path
    assert isdir(script.temp_path)


def test_correct_pip_version(script):
    """
    Check we are running proper version of pip in run_pip.
    """
    # output is like:
    # pip PIPVERSION from PIPDIRECTORY (python PYVERSION)
    result = script.pip('--version')

    # compare the directory tree of the invoked pip with that of this source
    # distribution
    dir = re.match(
        r'pip \d(\.[\d])+(\.?(rc|dev|pre|post)\d+)? from (.*) '
        r'\(python \d(.[\d])+\)$',
        result.stdout
    ).group(4)
    pip_folder = join(SRC_DIR, 'pip')
    pip_folder_outputed = join(dir, 'pip')

    diffs = filecmp.dircmp(pip_folder, pip_folder_outputed)

    # If any non-matching .py files exist, we have a problem: run_pip
    # is picking up some other version!  N.B. if this project acquires
    # primary resources other than .py files, this code will need
    # maintenance
    mismatch_py = [
        x for x in diffs.left_only + diffs.right_only + diffs.diff_files
        if x.endswith('.py')
    ]
    assert not mismatch_py, (
        'mismatched source files in %r and %r: %r' %
        (pip_folder, pip_folder_outputed, mismatch_py)
    )
