import os
import shutil
import tempfile

from mock import Mock
from pip.exceptions import PreviousBuildDirError
from pip.index import PackageFinder
from pip.log import logger
from pip.req import InstallRequirement, RequirementSet
from tests.lib import path_to_url, assert_raises_regexp, find_links


class TestRequirementSet(object):
    """RequirementSet tests"""

    def setup(self):
        logger.consumers = [(logger.NOTIFY, Mock())]
        self.tempdir = tempfile.mkdtemp()

    def teardown(self):
        logger.consumers = []
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def basic_reqset(self, skip_reqs={}):
        return RequirementSet(
            build_dir=os.path.join(self.tempdir, 'build'),
            src_dir=os.path.join(self.tempdir, 'src'),
            download_dir=None,
            download_cache=os.path.join(self.tempdir, 'download_cache'),
            skip_reqs=skip_reqs
            )

    def test_no_reuse_existing_build_dir(self):
        """Test prepare_files raise exception with previous build dir"""

        build_dir = os.path.join(self.tempdir, 'build', 'simple')
        os.makedirs(build_dir)
        open(os.path.join(build_dir, "setup.py"), 'w')
        reqset = self.basic_reqset()
        req = InstallRequirement.from_line('simple')
        reqset.add_requirement(req)
        finder = PackageFinder([find_links], [])
        assert_raises_regexp(
            PreviousBuildDirError,
            "pip can't proceed with [\s\S]*%s[\s\S]*%s" % (req, build_dir),
            reqset.prepare_files,
            finder
            )

    def test_skip_reqs(self):
        """Test the skip_reqs list works"""

        reqset = self.basic_reqset(skip_reqs={'simple':''})
        req = InstallRequirement.from_line('simple')
        reqset.add_requirement(req)
        assert not reqset.has_requirements
        finder = PackageFinder([find_links], [])
        reqset.prepare_files(finder)
        assert not reqset.has_requirements

    def test_add_requirement_returns_true_false(self):
        """Test add_requirement returns true of false"""

        req = InstallRequirement.from_line('simple')
        reqset = self.basic_reqset()
        assert True == reqset.add_requirement(req)
        reqset = self.basic_reqset(skip_reqs={'simple':''})
        assert False == reqset.add_requirement(req)
