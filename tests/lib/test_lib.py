"""Test the test support."""
import filecmp
import re
import sys
from contextlib import contextmanager
from os.path import isdir, join

import pytest

from tests.lib import SRC_DIR


@contextmanager
def assert_error_startswith(exc_type, expected_start):
    """
    Assert that an exception is raised starting with a certain message.
    """
    with pytest.raises(exc_type) as err:
        yield

    assert str(err.value).startswith(expected_start), f"full message: {err.value}"


def test_tmp_dir_exists_in_env(script):
    """
    Test that $TMPDIR == env.temp_path and path exists and env.assert_no_temp()
    passes (in fast env)
    """
    # need these tests to ensure the assert_no_temp feature of scripttest is
    # working
    script.assert_no_temp()  # this fails if env.tmp_path doesn't exist
    assert script.environ["TMPDIR"] == script.temp_path
    assert isdir(script.temp_path)


def test_correct_pip_version(script):
    """
    Check we are running proper version of pip in run_pip.
    """
    # output is like:
    # pip PIPVERSION from PIPDIRECTORY (python PYVERSION)
    result = script.pip("--version")

    # compare the directory tree of the invoked pip with that of this source
    # distribution
    pip_folder_outputed = re.match(
        r"pip \d+(\.[\d]+)+(\.?(b|rc|dev|pre|post)\d+)? from (.*) "
        r"\(python \d+(\.[\d]+)+\)$",
        result.stdout,
    ).group(4)
    pip_folder = join(SRC_DIR, "src", "pip")

    diffs = filecmp.dircmp(pip_folder, pip_folder_outputed)

    # If any non-matching .py files exist, we have a problem: run_pip
    # is picking up some other version!  N.B. if this project acquires
    # primary resources other than .py files, this code will need
    # maintenance
    mismatch_py = [
        x
        for x in diffs.left_only + diffs.right_only + diffs.diff_files
        if x.endswith(".py")
    ]
    assert not mismatch_py, (
        f"mismatched source files in {pip_folder!r} "
        f"and {pip_folder_outputed!r}: {mismatch_py!r}"
    )


def test_as_import(script):
    """test that pip.__init__.py does not shadow
    the command submodule with a dictionary
    """
    import pip._internal.commands.install as inst

    assert inst is not None


class TestPipTestEnvironment:
    def run_stderr_with_prefix(self, script, prefix, **kwargs):
        """
        Call run() that prints stderr with the given prefix.
        """
        text = f"{prefix}: hello, world\\n"
        command = f'import sys; sys.stderr.write("{text}")'
        args = [sys.executable, "-c", command]
        script.run(*args, **kwargs)

    def run_with_log_command(self, script, sub_string, **kwargs):
        """
        Call run() on a command that logs a "%"-style format string using
        the given substring as the string's replacement field.
        """
        command = (
            "import logging; logging.basicConfig(level='INFO'); "
            "logging.getLogger().info('sub: {}', 'foo')"
        ).format(sub_string)
        args = [sys.executable, "-c", command]
        script.run(*args, **kwargs)

    @pytest.mark.parametrize(
        "prefix",
        (
            "DEBUG",
            "INFO",
            "FOO",
        ),
    )
    def test_run__allowed_stderr(self, script, prefix):
        """
        Test calling run() with allowed stderr.
        """
        # Check that no error happens.
        self.run_stderr_with_prefix(script, prefix)

    def test_run__allow_stderr_warning(self, script):
        """
        Test passing allow_stderr_warning=True.
        """
        # Check that no error happens.
        self.run_stderr_with_prefix(
            script,
            "WARNING",
            allow_stderr_warning=True,
        )

        # Check that an error still happens with ERROR.
        expected_start = "stderr has an unexpected error"
        with assert_error_startswith(RuntimeError, expected_start):
            self.run_stderr_with_prefix(
                script,
                "ERROR",
                allow_stderr_warning=True,
            )

    @pytest.mark.parametrize(
        "prefix",
        (
            "DEPRECATION",
            "WARNING",
            "ERROR",
        ),
    )
    def test_run__allow_stderr_error(self, script, prefix):
        """
        Test passing allow_stderr_error=True.
        """
        # Check that no error happens.
        self.run_stderr_with_prefix(script, prefix, allow_stderr_error=True)

    @pytest.mark.parametrize(
        "prefix, expected_start",
        (
            ("DEPRECATION", "stderr has an unexpected warning"),
            ("WARNING", "stderr has an unexpected warning"),
            ("ERROR", "stderr has an unexpected error"),
        ),
    )
    def test_run__unexpected_stderr(self, script, prefix, expected_start):
        """
        Test calling run() with unexpected stderr output.
        """
        with assert_error_startswith(RuntimeError, expected_start):
            self.run_stderr_with_prefix(script, prefix)

    def test_run__logging_error(self, script):
        """
        Test calling run() with an unexpected logging error.
        """
        # Pass a good substitution string.
        self.run_with_log_command(script, sub_string="%r")

        expected_start = "stderr has a logging error, which is never allowed"
        with assert_error_startswith(RuntimeError, expected_start):
            # Pass a bad substitution string.  Also, pass
            # allow_stderr_error=True to check that the RuntimeError occurs
            # even under the stricter test condition of when we are allowing
            # other types of errors.
            self.run_with_log_command(
                script,
                sub_string="{!r}",
                allow_stderr_error=True,
            )

    def test_run__allow_stderr_error_false_error_with_expect_error(
        self,
        script,
    ):
        """
        Test passing allow_stderr_error=False with expect_error=True.
        """
        expected_start = "cannot pass allow_stderr_error=False with expect_error=True"
        with assert_error_startswith(RuntimeError, expected_start):
            script.run("python", allow_stderr_error=False, expect_error=True)

    def test_run__allow_stderr_warning_false_error_with_expect_stderr(
        self,
        script,
    ):
        """
        Test passing allow_stderr_warning=False with expect_stderr=True.
        """
        expected_start = (
            "cannot pass allow_stderr_warning=False with expect_stderr=True"
        )
        with assert_error_startswith(RuntimeError, expected_start):
            script.run(
                "python",
                allow_stderr_warning=False,
                expect_stderr=True,
            )

    @pytest.mark.parametrize(
        "arg_name",
        (
            "expect_error",
            "allow_stderr_error",
        ),
    )
    def test_run__allow_stderr_warning_false_error(self, script, arg_name):
        """
        Test passing allow_stderr_warning=False when it is not allowed.
        """
        kwargs = {"allow_stderr_warning": False, arg_name: True}
        expected_start = (
            "cannot pass allow_stderr_warning=False with allow_stderr_error=True"
        )
        with assert_error_startswith(RuntimeError, expected_start):
            script.run("python", **kwargs)

    def test_run__expect_error_fails_when_zero_returncode(self, script):
        expected_start = "Script passed unexpectedly"
        with assert_error_startswith(AssertionError, expected_start):
            script.run("python", expect_error=True)

    def test_run__no_expect_error_fails_when_nonzero_returncode(self, script):
        expected_start = "Script returned code: 1"
        with assert_error_startswith(AssertionError, expected_start):
            script.run("python", "-c", "import sys; sys.exit(1)")
