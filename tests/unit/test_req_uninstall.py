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
        monkeypatch.setattr(pip.req.req_uninstall, 'is_local', mock_is_local)
        # Fix case for windows tests
        file_extant = os.path.normcase(os.path.join(tmpdir, 'foo'))
        file_nonexistent = os.path.normcase(
            os.path.join(tmpdir, 'nonexistent'))
        with open(file_extant, 'w'):
            pass

        ups = UninstallPathSet(dist=Mock())
        assert ups.paths == set()
        ups.add(file_extant)
        assert ups.paths == set([file_extant])

        ups.add(file_nonexistent)
        assert ups.paths == set([file_extant])

    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_add_symlink(self, tmpdir, monkeypatch):
        monkeypatch.setattr(pip.req.req_uninstall, 'is_local', mock_is_local)
        f = os.path.join(tmpdir, 'foo')
        with open(f, 'w'):
            pass
        l = os.path.join(tmpdir, 'foo_link')
        os.symlink(f, l)

        ups = UninstallPathSet(dist=Mock())
        ups.add(l)
        assert ups.paths == set([l])

    def test_compact_shorter_path(self, monkeypatch):
        monkeypatch.setattr(pip.req.req_uninstall, 'is_local', lambda p: True)
        monkeypatch.setattr('os.path.exists', lambda p: True)
        # This deals with nt/posix path differences
        short_path = os.path.normcase(os.path.abspath(
            os.path.join(os.path.sep, 'path')))
        ups = UninstallPathSet(dist=Mock())
        ups.add(short_path)
        ups.add(os.path.join(short_path, 'longer'))
        assert ups.compact(ups.paths) == set([short_path])

    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_detect_symlink_dirs(self, monkeypatch, tmpdir):
        monkeypatch.setattr(pip.req.req_uninstall, 'is_local', lambda p: True)

        # construct 2 paths:
        #  tmpdir/dir/file
        #  tmpdir/dirlink/file (where dirlink is a link to dir)
        d = tmpdir.join('dir')
        d.mkdir()
        dlink = tmpdir.join('dirlink')
        os.symlink(d, dlink)
        d.join('file').touch()
        path1 = str(d.join('file'))
        path2 = str(dlink.join('file'))

        ups = UninstallPathSet(dist=Mock())
        ups.add(path1)
        ups.add(path2)
        assert ups.paths == set([path1])
