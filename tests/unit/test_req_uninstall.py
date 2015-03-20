import os

import pytest
from mock import Mock

import pip.req.req_uninstall
from pip.req.req_uninstall import UninstallPathSet


# Pretend all files are local, so UninstallPathSet accepts files in the tmpdir,
# outside the virtualenv
def mock_is_local(path):
    return True


class TestUninstallPathSet(object):
    def test_add(self, tmpdir, monkeypatch):
        monkeypatch.setattr(pip.utils, 'is_local', mock_is_local)
        file_extant = os.path.join(tmpdir, 'foo')
        file_nonexistant = os.path.join(tmpdir, 'nonexistant')
        with open(file_extant, 'w'):
            pass

        ups = UninstallPathSet(dist=Mock())
        assert ups.paths == set()
        ups.add(file_extant)
        assert ups.paths == set([file_extant])

        ups.add(file_nonexistant)
        assert ups.paths == set([file_extant])

    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_add_symlink(self, tmpdir, monkeypatch):
        monkeypatch.setattr(pip.utils, 'is_local', mock_is_local)
        f = os.path.join(tmpdir, 'foo')
        with open(f, 'w'):
            pass
        l = os.path.join(tmpdir, 'foo_link')
        os.symlink(f, l)

        ups = UninstallPathSet(dist=Mock())
        ups.add(l)
        assert ups.paths == set([l])
