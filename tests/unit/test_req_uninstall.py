import os

import pytest
from mock import Mock

import pip._internal.req.req_uninstall
from pip._internal.req.req_uninstall import (
    UninstallPathSet, compact, compress_for_output_listing,
    uninstallation_paths,
)
from tests.lib import create_file


# Pretend all files are local, so UninstallPathSet accepts files in the tmpdir,
# outside the virtualenv
def mock_is_local(path):
    return True


def test_uninstallation_paths():
    class dist(object):
        def get_metadata_lines(self, record):
            return ['file.py,,',
                    'file.pyc,,',
                    'file.so,,',
                    'nopyc.py']
        location = ''

    d = dist()

    paths = list(uninstallation_paths(d))

    expected = ['file.py',
                'file.pyc',
                'file.so',
                'nopyc.py',
                'nopyc.pyc']

    assert paths == expected

    # Avoid an easy 'unique generator' bug
    paths2 = list(uninstallation_paths(d))

    assert paths2 == paths


def test_compressed_listing(tmpdir):
    def in_tmpdir(paths):
        li = []
        for path in paths:
            li.append(str(os.path.normcase(
                os.path.join(tmpdir, path.replace("/", os.path.sep))
            )))
        return li

    sample = in_tmpdir([
        "lib/mypkg.dist-info/METADATA",
        "lib/mypkg.dist-info/PKG-INFO",
        "lib/mypkg/would_be_removed.txt",
        "lib/mypkg/would_be_skipped.skip.txt",
        "lib/mypkg/__init__.py",
        "lib/mypkg/my_awesome_code.py",
        "lib/mypkg/__pycache__/my_awesome_code-magic.pyc",
        "lib/mypkg/support/support_file.py",
        "lib/mypkg/support/more_support.py",
        "lib/mypkg/support/would_be_skipped.skip.py",
        "lib/mypkg/support/__pycache__/support_file-magic.pyc",
        "lib/random_other_place/file_without_a_dot_pyc",
        "bin/mybin",
    ])

    # Create the required files
    for fname in sample:
        create_file(fname, "random blub")

    # Remove the files to be skipped from the paths
    sample = [path for path in sample if ".skip." not in path]

    expected_remove = in_tmpdir([
        "bin/mybin",
        "lib/mypkg.dist-info/*",
        "lib/mypkg/*",
        "lib/random_other_place/file_without_a_dot_pyc",
    ])

    expected_skip = in_tmpdir([
        "lib/mypkg/would_be_skipped.skip.txt",
        "lib/mypkg/support/would_be_skipped.skip.py",
    ])

    will_remove, will_skip = compress_for_output_listing(sample)
    assert sorted(expected_skip) == sorted(compact(will_skip))
    assert sorted(expected_remove) == sorted(compact(will_remove))


class TestUninstallPathSet(object):
    def test_add(self, tmpdir, monkeypatch):
        monkeypatch.setattr(pip._internal.req.req_uninstall, 'is_local',
                            mock_is_local)
        # Fix case for windows tests
        file_extant = os.path.normcase(os.path.join(tmpdir, 'foo'))
        file_nonexistent = os.path.normcase(
            os.path.join(tmpdir, 'nonexistent'))
        with open(file_extant, 'w'):
            pass

        ups = UninstallPathSet(dist=Mock())
        assert ups.paths == set()
        ups.add(file_extant)
        assert ups.paths == {file_extant}

        ups.add(file_nonexistent)
        assert ups.paths == {file_extant}

    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_add_symlink(self, tmpdir, monkeypatch):
        monkeypatch.setattr(pip._internal.req.req_uninstall, 'is_local',
                            mock_is_local)
        f = os.path.join(tmpdir, 'foo')
        with open(f, 'w'):
            pass
        l = os.path.join(tmpdir, 'foo_link')
        os.symlink(f, l)

        ups = UninstallPathSet(dist=Mock())
        ups.add(l)
        assert ups.paths == {l}

    def test_compact_shorter_path(self, monkeypatch):
        monkeypatch.setattr(pip._internal.req.req_uninstall, 'is_local',
                            lambda p: True)
        monkeypatch.setattr('os.path.exists', lambda p: True)
        # This deals with nt/posix path differences
        short_path = os.path.normcase(os.path.abspath(
            os.path.join(os.path.sep, 'path')))
        ups = UninstallPathSet(dist=Mock())
        ups.add(short_path)
        ups.add(os.path.join(short_path, 'longer'))
        assert compact(ups.paths) == {short_path}

    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_detect_symlink_dirs(self, monkeypatch, tmpdir):
        monkeypatch.setattr(pip._internal.req.req_uninstall, 'is_local',
                            lambda p: True)

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
        assert ups.paths == {path1}
