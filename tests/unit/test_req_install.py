import os
import tempfile

import pytest

from pip.req.req_install import InstallRequirement


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
