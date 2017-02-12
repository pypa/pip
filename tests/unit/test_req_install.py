import os
import tempfile

import pytest
import mock
from pip.req.req_install import InstallRequirement
from pip._vendor.packaging.requirements import Requirement


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

    @pytest.mark.parametrize(
        "installed_requires,confirm_answer",
        [
            ((), None),
            (("dummy",), 'y'),
            pytest.mark.xfail((("dummy",), 'n')),
        ],
    )
    def test_confirm_dependencies(self, installed_requires, confirm_answer):

        with mock.patch('pip.req.req_install.ask') as mock_ask:
            mock_ask.return_value = confirm_answer
            class req(Requirement):
                def __init__(self, key):
                    self.key = key

            class installed(object):
                def __init__(self, requires):
                    self._requires = [req(r) for r in requires]

                def requires(self):
                    return self._requires

            comes_from = None
            requirement = InstallRequirement(Requirement("dummy"), None)
            installed_packages = [installed(installed_requires)]
            assert requirement.confirm_dependencies(installed_packages)
            if confirm_answer:
                mock_ask.assert_called_with('Proceed (y/n)? ', ('y', 'n'))
