import sys
import os
import tempfile
import shutil

from pip.exceptions import PreviousBuildDirError
from pip.index import PackageFinder
from pip.log import logger
from pip.req import InstallRequirement, RequirementSet
from tests.test_pip import here, path_to_url, assert_raises_regexp

find_links = path_to_url(os.path.join(here, 'packages'))

class TestRequirementSet(object):
    """RequirementSet tests"""

    def setup(self):
        logger.consumers = [(logger.NOTIFY, sys.stdout)]
        self.tempdir = tempfile.mkdtemp()

    def teardown(self):
        logger.consumers = []
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def basic_reqset(self):
        return RequirementSet(
            build_dir=os.path.join(self.tempdir, 'build'),
            src_dir=os.path.join(self.tempdir, 'src'),
            download_dir=None,
            download_cache=os.path.join(self.tempdir, 'download_cache'),
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

