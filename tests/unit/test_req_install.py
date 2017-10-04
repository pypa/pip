import os
import tempfile

import pytest

from pip._internal.req.req_install import InstallRequirement


class TestInstallRequirementBuildDirectory(object):
    # no need to test symlinks on Windows
    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_tmp_build_directory(self):
        # when req is None, we can produce a temporary directory
        # Make sure we're handling it correctly with real path.
        requirement = InstallRequirement(None, None)
        tmp_dir = tempfile.mkdtemp('-build', 'pip-')
        tmp_build_dir = requirement.build_location(tmp_dir)
        assert (
            os.path.dirname(tmp_build_dir) ==
            os.path.realpath(os.path.dirname(tmp_dir))
        )
        # are we on a system where /tmp is a symlink
        if os.path.realpath(tmp_dir) != os.path.abspath(tmp_dir):
            assert os.path.dirname(tmp_build_dir) != os.path.dirname(tmp_dir)
        else:
            assert os.path.dirname(tmp_build_dir) == os.path.dirname(tmp_dir)
        os.rmdir(tmp_dir)
        assert not os.path.exists(tmp_dir)

    def test_forward_slash_results_in_a_link(self, tmpdir):
        install_dir = tmpdir / "foo" / "bar"

        # Just create a file for letting the logic work
        setup_py_path = install_dir / "setup.py"
        os.makedirs(str(install_dir))
        with open(setup_py_path, 'w') as f:
            f.write('')

        requirement = InstallRequirement.from_line(
            str(install_dir).replace(os.sep, os.altsep or os.sep)
        )

        assert requirement.link is not None
