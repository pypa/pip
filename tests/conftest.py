import distutils.sysconfig
import os
import os.path
import subprocess
import sys

import pytest
import scripttest
import virtualenv as _virtualenv


class PipTestFileEnvironment(scripttest.TestFileEnvironment):

    def __init__(self, base_path, *args, **kwargs):
        self.virtualenv = kwargs.pop("virtualenv")

        environ = kwargs.setdefault("environ", os.environ.copy())

        # Make sure our log file goes into our base_directory
        environ["PIP_LOG_FILE"] = os.path.join(base_path, "pip-log.txt")

        # Put the virtual environment's bin path first on the $PATH
        environ["PATH"] = os.pathsep.join(
            [str(self.virtualenv.join("bin"))] + [environ.get("PATH", [])],
        )

        super(PipTestFileEnvironment, self).__init__(
            base_path, *args, **kwargs
        )

    def pip(self, *args, **kwargs):
        return self.run("pip", *args, **kwargs)


@pytest.fixture
def virtualenv(tmpdir):
    where = tmpdir.join("env")

    # Create a virtual environment without pip
    _virtualenv.create_environment(str(where),
        clear=True,
        never_download=True,
        no_pip=True,
    )

    # On Python < 3.3 we don't have subprocess.DEVNULL
    try:
        devnull = subprocess.DEVNULL
    except AttributeError:
        devnull = open(os.devnull, "wb")

    # Install our development version of pip install the virtual environment
    p = subprocess.Popen(
        [
            str(where.join("bin/python")), "setup.py", "install",
            # These values are taken from pip, to better match what pip install
            #   would give us
            "--record", str(tmpdir.join("pip-record.txt")),
            "--single-version-externally-managed",
            "--install-headers", os.path.join(
                sys.prefix, "include", "site",
                "python" + distutils.sysconfig.get_python_version(),
            ),
        ],
        stderr=subprocess.STDOUT,
        stdout=devnull,
    )
    p.communicate()

    if p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, p.args)

    return where


@pytest.fixture
def script(tmpdir, virtualenv):
    # Create our workspace directory
    workspace = tmpdir.join("workspace")
    workspace.mkdir()

    # Create & return the script runner
    return PipTestFileEnvironment(str(tmpdir.join("script-test")),
        cwd=str(tmpdir.join("workspace")),
        virtualenv=virtualenv,
        capture_temp=True,
        assert_no_temp=True,
    )
