import os
import shutil
from shutil import rmtree
from tempfile import mkdtemp
from unittest.mock import Mock, patch

import pytest

from pip._internal.exceptions import HashMismatch
from pip._internal.models.link import Link
from pip._internal.network.download import Downloader
from pip._internal.network.session import PipSession
from pip._internal.operations.prepare import _copy_source_tree, unpack_url
from pip._internal.utils.hashes import Hashes
from pip._internal.utils.urls import path_to_url
from tests.lib.filesystem import get_filelist, make_socket_file, make_unreadable_file
from tests.lib.path import Path
from tests.lib.requests_mocks import MockResponse


def test_unpack_url_with_urllib_response_without_content_type(data):
    """
    It should download and unpack files even if no Content-Type header exists
    """
    _real_session = PipSession()

    def _fake_session_get(*args, **kwargs):
        resp = _real_session.get(*args, **kwargs)
        del resp.headers["Content-Type"]
        return resp

    session = Mock()
    session.get = _fake_session_get
    download = Downloader(session, progress_bar="on")

    uri = path_to_url(data.packages.joinpath("simple-1.0.tar.gz"))
    link = Link(uri)
    temp_dir = mkdtemp()
    try:
        unpack_url(
            link,
            temp_dir,
            download=download,
            download_dir=None,
        )
        assert set(os.listdir(temp_dir)) == {
            "PKG-INFO",
            "setup.cfg",
            "setup.py",
            "simple",
            "simple.egg-info",
        }
    finally:
        rmtree(temp_dir)


@patch("pip._internal.network.download.raise_for_status")
def test_download_http_url__no_directory_traversal(mock_raise_for_status, tmpdir):
    """
    Test that directory traversal doesn't happen on download when the
    Content-Disposition header contains a filename with a ".." path part.
    """
    mock_url = "http://www.example.com/whatever.tgz"
    contents = b"downloaded"
    link = Link(mock_url)

    session = Mock()
    resp = MockResponse(contents)
    resp.url = mock_url
    resp.headers = {
        # Set the content-type to a random value to prevent
        # mimetypes.guess_extension from guessing the extension.
        "content-type": "random",
        "content-disposition": 'attachment;filename="../out_dir_file"',
    }
    session.get.return_value = resp
    download = Downloader(session, progress_bar="on")

    download_dir = tmpdir.joinpath("download")
    os.mkdir(download_dir)
    file_path, content_type = download(link, download_dir)
    # The file should be downloaded to download_dir.
    actual = os.listdir(download_dir)
    assert actual == ["out_dir_file"]
    mock_raise_for_status.assert_called_once_with(resp)


@pytest.fixture
def clean_project(tmpdir_factory, data):
    tmpdir = Path(str(tmpdir_factory.mktemp("clean_project")))
    new_project_dir = tmpdir.joinpath("FSPkg")
    path = data.packages.joinpath("FSPkg")
    shutil.copytree(path, new_project_dir)
    return new_project_dir


def test_copy_source_tree(clean_project, tmpdir):
    target = tmpdir.joinpath("target")
    expected_files = get_filelist(clean_project)
    assert len(expected_files) == 3

    _copy_source_tree(clean_project, target)

    copied_files = get_filelist(target)
    assert expected_files == copied_files


@pytest.mark.skipif("sys.platform == 'win32'")
def test_copy_source_tree_with_socket(clean_project, tmpdir, caplog):
    target = tmpdir.joinpath("target")
    expected_files = get_filelist(clean_project)
    socket_path = str(clean_project.joinpath("aaa"))
    make_socket_file(socket_path)

    _copy_source_tree(clean_project, target)

    copied_files = get_filelist(target)
    assert expected_files == copied_files

    # Warning should have been logged.
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == "WARNING"
    assert socket_path in record.message


@pytest.mark.skipif("sys.platform == 'win32'")
def test_copy_source_tree_with_socket_fails_with_no_socket_error(clean_project, tmpdir):
    target = tmpdir.joinpath("target")
    expected_files = get_filelist(clean_project)
    make_socket_file(clean_project.joinpath("aaa"))
    unreadable_file = clean_project.joinpath("bbb")
    make_unreadable_file(unreadable_file)

    with pytest.raises(shutil.Error) as e:
        _copy_source_tree(clean_project, target)

    errored_files = [err[0] for err in e.value.args[0]]
    assert len(errored_files) == 1
    assert unreadable_file in errored_files

    copied_files = get_filelist(target)
    # All files without errors should have been copied.
    assert expected_files == copied_files


def test_copy_source_tree_with_unreadable_dir_fails(clean_project, tmpdir):
    target = tmpdir.joinpath("target")
    expected_files = get_filelist(clean_project)
    unreadable_file = clean_project.joinpath("bbb")
    make_unreadable_file(unreadable_file)

    with pytest.raises(shutil.Error) as e:
        _copy_source_tree(clean_project, target)

    errored_files = [err[0] for err in e.value.args[0]]
    assert len(errored_files) == 1
    assert unreadable_file in errored_files

    copied_files = get_filelist(target)
    # All files without errors should have been copied.
    assert expected_files == copied_files


class Test_unpack_url:
    def prep(self, tmpdir, data):
        self.build_dir = tmpdir.joinpath("build")
        self.download_dir = tmpdir.joinpath("download")
        os.mkdir(self.build_dir)
        os.mkdir(self.download_dir)
        self.dist_file = "simple-1.0.tar.gz"
        self.dist_file2 = "simple-2.0.tar.gz"
        self.dist_path = data.packages.joinpath(self.dist_file)
        self.dist_path2 = data.packages.joinpath(self.dist_file2)
        self.dist_url = Link(path_to_url(self.dist_path))
        self.dist_url2 = Link(path_to_url(self.dist_path2))
        self.no_download = Mock(side_effect=AssertionError)

    def test_unpack_url_no_download(self, tmpdir, data):
        self.prep(tmpdir, data)
        unpack_url(self.dist_url, self.build_dir, self.no_download)
        assert os.path.isdir(os.path.join(self.build_dir, "simple"))
        assert not os.path.isfile(os.path.join(self.download_dir, self.dist_file))

    def test_unpack_url_bad_hash(self, tmpdir, data):
        """
        Test when the file url hash fragment is wrong
        """
        self.prep(tmpdir, data)
        url = f"{self.dist_url.url}#md5=bogus"
        dist_url = Link(url)
        with pytest.raises(HashMismatch):
            unpack_url(
                dist_url,
                self.build_dir,
                download=self.no_download,
                hashes=Hashes({"md5": ["bogus"]}),
            )

    def test_unpack_url_thats_a_dir(self, tmpdir, data):
        self.prep(tmpdir, data)
        dist_path = data.packages.joinpath("FSPkg")
        dist_url = Link(path_to_url(dist_path))
        unpack_url(
            dist_url,
            self.build_dir,
            download=self.no_download,
            download_dir=self.download_dir,
        )
        assert os.path.isdir(os.path.join(self.build_dir, "fspkg"))


@pytest.mark.parametrize("exclude_dir", [".nox", ".tox"])
def test_unpack_url_excludes_expected_dirs(tmpdir, exclude_dir):
    src_dir = tmpdir / "src"
    dst_dir = tmpdir / "dst"
    src_included_file = src_dir.joinpath("file.txt")
    src_excluded_dir = src_dir.joinpath(exclude_dir)
    src_excluded_file = src_dir.joinpath(exclude_dir, "file.txt")
    src_included_dir = src_dir.joinpath("subdir", exclude_dir)

    # set up source directory
    src_excluded_dir.mkdir(parents=True)
    src_included_dir.mkdir(parents=True)
    src_included_file.touch()
    src_excluded_file.touch()

    dst_included_file = dst_dir.joinpath("file.txt")
    dst_excluded_dir = dst_dir.joinpath(exclude_dir)
    dst_excluded_file = dst_dir.joinpath(exclude_dir, "file.txt")
    dst_included_dir = dst_dir.joinpath("subdir", exclude_dir)

    src_link = Link(path_to_url(src_dir))
    unpack_url(src_link, dst_dir, Mock(side_effect=AssertionError), download_dir=None)
    assert not os.path.isdir(dst_excluded_dir)
    assert not os.path.isfile(dst_excluded_file)
    assert os.path.isfile(dst_included_file)
    assert os.path.isdir(dst_included_dir)
