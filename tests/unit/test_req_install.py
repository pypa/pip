import os
import tempfile

import pytest

from pip._internal.index import InstallationCandidate
from pip._internal.req.req_install import InstallRequirement


class MockedFinder(object):

    def __init__(self, ret):
        self.ret = ret

    def find_requirement(self, req, upgrade):
        return self.ret


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

    def test_install_requirement_version_is_correct(self, tmpdir):
        install_dir = tmpdir / "foo" / "bar"

        # Just create a file for letting the logic work
        setup_py_path = install_dir / "setup.py"
        os.makedirs(str(install_dir))
        with open(setup_py_path, 'w') as f:
            f.write('')

        requirement1 = InstallRequirement.from_line(
            'https://example.com/urllib3.tar.gz',
        )
        requirement2 = InstallRequirement.from_line(
            'https://example.com/urllib3-1.22-py2.py3-none-any.whl',
        )
        requirement3 = InstallRequirement.from_line(
            'urllib3==1.22',
        )
        mocked_finder = MockedFinder(
            InstallationCandidate(
                'urllib3', '1.4', 'https://example.com/urllib3.tar.gz'))
        requirement3.populate_link(mocked_finder, False, False)

        assert requirement1.link is not None
        assert requirement1.version is None
        assert requirement2.link is not None
        assert requirement2.version == "1.22"
        assert requirement3.link is not None
        assert requirement3.version == "1.4"
