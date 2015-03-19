import os
import shutil
import sys
import tempfile

import pytest
from mock import Mock

from pip.locations import running_under_virtualenv
from pip.req.req_uninstall import UninstallPathSet

class TestUninstallPathSet(object):
    def setup(self):
        if running_under_virtualenv():
            # Construct tempdir in sys.prefix, otherwise UninstallPathSet
            # will reject paths.
            self.tempdir = tempfile.mkdtemp(prefix=sys.prefix)
        else:
            self.tempdir = tempfile.mkdtemp()

    def teardown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_add(self):
        file_extant = os.path.join(self.tempdir, 'foo')
        file_nonexistant = os.path.join(self.tempdir, 'nonexistant')
        with open(file_extant, 'w'): pass

        ups = UninstallPathSet(dist=Mock())
        assert ups.paths == set()
        ups.add(file_extant)
        assert ups.paths == set([file_extant])

        ups.add(file_nonexistant)
        assert ups.paths == set([file_extant])

    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_add_symlink(self):
        f = os.path.join(self.tempdir, 'foo')
        with open(f, 'w'): pass
        l = os.path.join(self.tempdir, 'foo_link')
        os.symlink(f, l)

        ups = UninstallPathSet(dist=Mock())
        ups.add(l)
        assert ups.paths == set([l])
