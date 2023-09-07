import contextlib
import email.message
import os
import shutil
import sys
import tempfile
from functools import partial
from pathlib import Path
from typing import Iterator, Optional, Tuple, cast
from unittest import mock

import pytest
from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.requirements import Requirement

from pip._internal.cache import WheelCache
from pip._internal.commands import create_command
from pip._internal.commands.install import InstallCommand
from pip._internal.exceptions import (
    HashErrors,
    InstallationError,
    InvalidWheelFilename,
    PreviousBuildDirError,
)
from pip._internal.index.package_finder import PackageFinder
from pip._internal.models.direct_url import ArchiveInfo, DirectUrl, DirInfo, VcsInfo
from pip._internal.models.link import Link
from pip._internal.network.session import PipSession
from pip._internal.operations.build.build_tracker import get_build_tracker
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req import InstallRequirement, RequirementSet
from pip._internal.req.constructors import (
    _get_url_from_path,
    _looks_like_path,
    install_req_from_editable,
    install_req_from_line,
    install_req_from_parsed_requirement,
    install_req_from_req_string,
    parse_editable,
)
from pip._internal.req.req_file import (
    ParsedLine,
    get_line_parser,
    handle_requirement_line,
)
from pip._internal.resolution.legacy.resolver import Resolver
from tests.lib import TestData, make_test_finder, requirements_file, wheel


def get_processed_req_from_line(
    line: str, fname: str = "file", lineno: int = 1
) -> InstallRequirement:
    line_parser = get_line_parser(None)
    args_str, opts = line_parser(line)
    parsed_line = ParsedLine(
        fname,
        lineno,
        args_str,
        opts,
        False,
    )
    parsed_req = handle_requirement_line(parsed_line)
    assert parsed_req is not None
    req = install_req_from_parsed_requirement(parsed_req)
    req.user_supplied = True
    return req


class TestRequirementSet:
    """RequirementSet tests"""

    def setup_method(self) -> None:
        self.tempdir = tempfile.mkdtemp()

    def teardown_method(self) -> None:
        shutil.rmtree(self.tempdir, ignore_errors=True)

    @contextlib.contextmanager
    def _basic_resolver(
        self,
        finder: PackageFinder,
        require_hashes: bool = False,
        wheel_cache: Optional[WheelCache] = None,
    ) -> Iterator[Resolver]:
        make_install_req = partial(
            install_req_from_req_string,
            isolated=False,
            use_pep517=None,
        )
        session = PipSession()

        with get_build_tracker() as tracker:
            preparer = RequirementPreparer(
                build_dir=os.path.join(self.tempdir, "build"),
                src_dir=os.path.join(self.tempdir, "src"),
                download_dir=None,
                build_isolation=True,
                check_build_deps=False,
                build_tracker=tracker,
                session=session,
                progress_bar="on",
                finder=finder,
                require_hashes=require_hashes,
                use_user_site=False,
                lazy_wheel=False,
                verbosity=0,
                legacy_resolver=True,
            )
            yield Resolver(
                preparer=preparer,
                make_install_req=make_install_req,
                finder=finder,
                wheel_cache=wheel_cache,
                use_user_site=False,
                upgrade_strategy="to-satisfy-only",
                ignore_dependencies=False,
                ignore_installed=False,
                ignore_requires_python=False,
                force_reinstall=False,
            )

    def test_no_reuse_existing_build_dir(self, data: TestData) -> None:
        """Test prepare_files raise exception with previous build dir"""

        build_dir = os.path.join(self.tempdir, "build", "simple")
        os.makedirs(build_dir)
        with open(os.path.join(build_dir, "setup.py"), "w"):
            pass
        reqset = RequirementSet()
        req = install_req_from_line("simple")
        req.user_supplied = True
        reqset.add_named_requirement(req)
        finder = make_test_finder(find_links=[data.find_links])
        with self._basic_resolver(finder) as resolver:
            with pytest.raises(
                PreviousBuildDirError,
                match=(
                    r"pip can't proceed with [\s\S]*{req}[\s\S]*{build_dir_esc}".format(
                        build_dir_esc=build_dir.replace("\\", "\\\\"), req=req
                    )
                ),
            ):
                resolver.resolve(reqset.all_requirements, True)

    def test_environment_marker_extras(self, data: TestData) -> None:
        """
        Test that the environment marker extras are used with
        non-wheel installs.
        """
        reqset = RequirementSet()
        req = install_req_from_editable(
            os.fspath(data.packages.joinpath("LocalEnvironMarker")),
        )
        req.user_supplied = True
        reqset.add_unnamed_requirement(req)
        finder = make_test_finder(find_links=[data.find_links])
        with self._basic_resolver(finder) as resolver:
            reqset = resolver.resolve(reqset.all_requirements, True)
        assert not reqset.has_requirement("simple")

    def test_missing_hash_with_require_hashes(self, data: TestData) -> None:
        """Setting --require-hashes explicitly should raise errors if hashes
        are missing.
        """
        reqset = RequirementSet()
        reqset.add_named_requirement(
            get_processed_req_from_line("simple==1.0", lineno=1)
        )

        finder = make_test_finder(find_links=[data.find_links])

        with self._basic_resolver(finder, require_hashes=True) as resolver:
            with pytest.raises(
                HashErrors,
                match=(
                    r"Hashes are required in --require-hashes mode, but they are "
                    r"missing .*\n"
                    r"    simple==1.0 --hash=sha256:393043e672415891885c9a2a0929b1"
                    r"af95fb866d6ca016b42d2e6ce53619b653$"
                ),
            ):
                resolver.resolve(reqset.all_requirements, True)

    def test_missing_hash_with_require_hashes_in_reqs_file(
        self, data: TestData, tmpdir: Path
    ) -> None:
        """--require-hashes in a requirements file should make its way to the
        RequirementSet.
        """
        finder = make_test_finder(find_links=[data.find_links])
        session = finder._link_collector.session
        command = cast(InstallCommand, create_command("install"))
        with requirements_file("--require-hashes", tmpdir) as reqs_file:
            options, args = command.parse_args(["-r", os.fspath(reqs_file)])
            command.get_requirements(args, options, finder, session)
        assert options.require_hashes

    def test_unsupported_hashes(self, data: TestData) -> None:
        """VCS and dir links should raise errors when --require-hashes is
        on.

        In addition, complaints about the type of requirement (VCS or dir)
        should trump the presence or absence of a hash.

        """
        reqset = RequirementSet()
        reqset.add_unnamed_requirement(
            get_processed_req_from_line(
                "git+git://github.com/pypa/pip-test-package --hash=sha256:123",
                lineno=1,
            )
        )
        dir_path = data.packages.joinpath("FSPkg")
        reqset.add_unnamed_requirement(
            get_processed_req_from_line(
                f"file://{dir_path}",
                lineno=2,
            )
        )
        finder = make_test_finder(find_links=[data.find_links])

        sep = os.path.sep
        if sep == "\\":
            sep = "\\\\"  # This needs to be escaped for the regex

        with self._basic_resolver(finder, require_hashes=True) as resolver:
            with pytest.raises(
                HashErrors,
                match=(
                    r"Can't verify hashes for these requirements because we don't "
                    r"have a way to hash version control repositories:\n"
                    r"    git\+git://github\.com/pypa/pip-test-package \(from -r "
                    r"file \(line 1\)\)\n"
                    r"Can't verify hashes for these file:// requirements because "
                    r"they point to directories:\n"
                    r"    file://.*{sep}data{sep}packages{sep}FSPkg "
                    r"\(from -r file \(line 2\)\)".format(sep=sep)
                ),
            ):
                resolver.resolve(reqset.all_requirements, True)

    def test_unpinned_hash_checking(self, data: TestData) -> None:
        """Make sure prepare_files() raises an error when a requirement is not
        version-pinned in hash-checking mode.
        """
        reqset = RequirementSet()
        # Test that there must be exactly 1 specifier:
        reqset.add_named_requirement(
            get_processed_req_from_line(
                "simple --hash=sha256:a90427ae31f5d1d0d7ec06ee97d9fcf2d0fc9a786985"
                "250c1c83fd68df5911dd",
                lineno=1,
            )
        )
        # Test that the operator must be ==:
        reqset.add_named_requirement(
            get_processed_req_from_line(
                "simple2>1.0 --hash=sha256:3ad45e1e9aa48b4462af0"
                "123f6a7e44a9115db1ef945d4d92c123dfe21815a06",
                lineno=2,
            )
        )
        finder = make_test_finder(find_links=[data.find_links])
        with self._basic_resolver(finder, require_hashes=True) as resolver:
            with pytest.raises(
                HashErrors,
                # Make sure all failing requirements are listed:
                match=(
                    r"versions pinned with ==. These do not:\n"
                    r"    simple .* \(from -r file \(line 1\)\)\n"
                    r"    simple2>1.0 .* \(from -r file \(line 2\)\)"
                ),
            ):
                resolver.resolve(reqset.all_requirements, True)

    def test_hash_mismatch(self, data: TestData) -> None:
        """A hash mismatch should raise an error."""
        file_url = data.packages.joinpath("simple-1.0.tar.gz").resolve().as_uri()
        reqset = RequirementSet()
        reqset.add_unnamed_requirement(
            get_processed_req_from_line(
                f"{file_url} --hash=sha256:badbad",
                lineno=1,
            )
        )
        finder = make_test_finder(find_links=[data.find_links])
        with self._basic_resolver(finder, require_hashes=True) as resolver:
            with pytest.raises(
                HashErrors,
                match=(
                    r"THESE PACKAGES DO NOT MATCH THE HASHES.*\n"
                    r"    file:///.*/data/packages/simple-1\.0\.tar\.gz .*:\n"
                    r"        Expected sha256 badbad\n"
                    r"             Got        393043e672415891885c9a2a0929b1af95fb"
                    r"866d6ca016b42d2e6ce53619b653$"
                ),
            ):
                resolver.resolve(reqset.all_requirements, True)

    def test_unhashed_deps_on_require_hashes(self, data: TestData) -> None:
        """Make sure unhashed, unpinned, or otherwise unrepeatable
        dependencies get complained about when --require-hashes is on."""
        reqset = RequirementSet()
        finder = make_test_finder(find_links=[data.find_links])
        reqset.add_named_requirement(
            get_processed_req_from_line(
                "TopoRequires2==0.0.1 "  # requires TopoRequires
                "--hash=sha256:eaf9a01242c9f2f42cf2bd82a6a848cd"
                "e3591d14f7896bdbefcf48543720c970",
                lineno=1,
            )
        )

        with self._basic_resolver(finder, require_hashes=True) as resolver:
            with pytest.raises(
                HashErrors,
                match=(
                    r"In --require-hashes mode, all requirements must have their "
                    r"versions pinned.*\n"
                    r"    TopoRequires from .*$"
                ),
            ):
                resolver.resolve(reqset.all_requirements, True)

    def test_hashed_deps_on_require_hashes(self) -> None:
        """Make sure hashed dependencies get installed when --require-hashes
        is on.

        (We actually just check that no "not all dependencies are hashed!"
        error gets raised while preparing; there is no reason to expect
        installation to then fail, as the code paths are the same as ever.)

        """
        reqset = RequirementSet()
        reqset.add_named_requirement(
            get_processed_req_from_line(
                "TopoRequires2==0.0.1 "  # requires TopoRequires
                "--hash=sha256:eaf9a01242c9f2f42cf2bd82a6a848cd"
                "e3591d14f7896bdbefcf48543720c970",
                lineno=1,
            )
        )
        reqset.add_named_requirement(
            get_processed_req_from_line(
                "TopoRequires==0.0.1 "
                "--hash=sha256:d6dd1e22e60df512fdcf3640ced3039b3b02a56ab2cee81ebcb"
                "3d0a6d4e8bfa6",
                lineno=2,
            )
        )

    def test_download_info_find_links(self, data: TestData) -> None:
        """Test that download_info is set for requirements via find_links."""
        finder = make_test_finder(find_links=[data.find_links])
        with self._basic_resolver(finder) as resolver:
            ireq = get_processed_req_from_line("simple")
            reqset = resolver.resolve([ireq], True)
            assert len(reqset.all_requirements) == 1
            req = reqset.all_requirements[0]
            assert req.download_info
            assert isinstance(req.download_info.info, ArchiveInfo)
            assert req.download_info.info.hash

    @pytest.mark.network
    def test_download_info_index_url(self) -> None:
        """Test that download_info is set for requirements via index."""
        finder = make_test_finder(index_urls=["https://pypi.org/simple"])
        with self._basic_resolver(finder) as resolver:
            ireq = get_processed_req_from_line("initools")
            reqset = resolver.resolve([ireq], True)
            assert len(reqset.all_requirements) == 1
            req = reqset.all_requirements[0]
            assert req.download_info
            assert isinstance(req.download_info.info, ArchiveInfo)

    @pytest.mark.network
    def test_download_info_web_archive(self) -> None:
        """Test that download_info is set for requirements from a web archive."""
        finder = make_test_finder()
        with self._basic_resolver(finder) as resolver:
            ireq = get_processed_req_from_line(
                "pip-test-package @ "
                "https://github.com/pypa/pip-test-package/tarball/0.1.1"
            )
            reqset = resolver.resolve([ireq], True)
            assert len(reqset.all_requirements) == 1
            req = reqset.all_requirements[0]
            assert req.download_info
            assert (
                req.download_info.url
                == "https://github.com/pypa/pip-test-package/tarball/0.1.1"
            )
            assert isinstance(req.download_info.info, ArchiveInfo)
            assert (
                req.download_info.info.hash == "sha256="
                "ad977496000576e1b6c41f6449a9897087ce9da6db4f15b603fe8372af4bf3c6"
            )

    def test_download_info_archive_legacy_cache(
        self, tmp_path: Path, shared_data: TestData
    ) -> None:
        """Test download_info hash is not set for an archive with legacy cache entry."""
        url = shared_data.packages.joinpath("simple-1.0.tar.gz").as_uri()
        finder = make_test_finder()
        wheel_cache = WheelCache(str(tmp_path / "cache"))
        cache_entry_dir = wheel_cache.get_path_for_link(Link(url))
        Path(cache_entry_dir).mkdir(parents=True)
        wheel.make_wheel(name="simple", version="1.0").save_to_dir(cache_entry_dir)
        with self._basic_resolver(finder, wheel_cache=wheel_cache) as resolver:
            ireq = get_processed_req_from_line(f"simple @ {url}")
            reqset = resolver.resolve([ireq], True)
            assert len(reqset.all_requirements) == 1
            req = reqset.all_requirements[0]
            assert req.is_wheel_from_cache
            assert req.cached_wheel_source_link
            assert req.download_info
            assert req.download_info.url == url
            assert isinstance(req.download_info.info, ArchiveInfo)
            assert not req.download_info.info.hash

    def test_download_info_archive_cache_with_origin(
        self, tmp_path: Path, shared_data: TestData
    ) -> None:
        """Test download_info hash is set for a web archive with cache entry
        that has origin.json."""
        url = shared_data.packages.joinpath("simple-1.0.tar.gz").as_uri()
        hash = "sha256=ad977496000576e1b6c41f6449a9897087ce9da6db4f15b603fe8372af4bf3c6"
        finder = make_test_finder()
        wheel_cache = WheelCache(str(tmp_path / "cache"))
        cache_entry_dir = wheel_cache.get_path_for_link(Link(url))
        Path(cache_entry_dir).mkdir(parents=True)
        Path(cache_entry_dir).joinpath("origin.json").write_text(
            DirectUrl(url, ArchiveInfo(hash=hash)).to_json()
        )
        wheel.make_wheel(name="simple", version="1.0").save_to_dir(cache_entry_dir)
        with self._basic_resolver(finder, wheel_cache=wheel_cache) as resolver:
            ireq = get_processed_req_from_line(f"simple @ {url}")
            reqset = resolver.resolve([ireq], True)
            assert len(reqset.all_requirements) == 1
            req = reqset.all_requirements[0]
            assert req.is_wheel_from_cache
            assert req.cached_wheel_source_link
            assert req.download_info
            assert req.download_info.url == url
            assert isinstance(req.download_info.info, ArchiveInfo)
            assert req.download_info.info.hash == hash

    def test_download_info_archive_cache_with_invalid_origin(
        self, tmp_path: Path, shared_data: TestData, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test an invalid origin.json is ignored."""
        url = shared_data.packages.joinpath("simple-1.0.tar.gz").as_uri()
        finder = make_test_finder()
        wheel_cache = WheelCache(str(tmp_path / "cache"))
        cache_entry_dir = wheel_cache.get_path_for_link(Link(url))
        Path(cache_entry_dir).mkdir(parents=True)
        Path(cache_entry_dir).joinpath("origin.json").write_text("{")  # invalid json
        wheel.make_wheel(name="simple", version="1.0").save_to_dir(cache_entry_dir)
        with self._basic_resolver(finder, wheel_cache=wheel_cache) as resolver:
            ireq = get_processed_req_from_line(f"simple @ {url}")
            reqset = resolver.resolve([ireq], True)
            assert len(reqset.all_requirements) == 1
            req = reqset.all_requirements[0]
            assert req.is_wheel_from_cache
            assert "Ignoring invalid cache entry origin file" in caplog.messages[0]

    def test_download_info_local_wheel(self, data: TestData) -> None:
        """Test that download_info is set for requirements from a local wheel."""
        finder = make_test_finder()
        with self._basic_resolver(finder) as resolver:
            ireq = get_processed_req_from_line(
                f"{data.packages}/simplewheel-1.0-py2.py3-none-any.whl"
            )
            reqset = resolver.resolve([ireq], True)
            assert len(reqset.all_requirements) == 1
            req = reqset.all_requirements[0]
            assert req.download_info
            assert req.download_info.url.startswith("file://")
            assert isinstance(req.download_info.info, ArchiveInfo)
            assert (
                req.download_info.info.hash == "sha256="
                "e63aa139caee941ec7f33f057a5b987708c2128238357cf905429846a2008718"
            )

    def test_download_info_local_dir(self, data: TestData) -> None:
        """Test that download_info is set for requirements from a local dir."""
        finder = make_test_finder()
        with self._basic_resolver(finder) as resolver:
            ireq_url = data.packages.joinpath("FSPkg").as_uri()
            ireq = get_processed_req_from_line(f"FSPkg @ {ireq_url}")
            reqset = resolver.resolve([ireq], True)
            assert len(reqset.all_requirements) == 1
            req = reqset.all_requirements[0]
            assert req.download_info
            assert req.download_info.url.startswith("file://")
            assert isinstance(req.download_info.info, DirInfo)

    def test_download_info_local_editable_dir(self, data: TestData) -> None:
        """Test that download_info is set for requirements from a local editable dir."""
        finder = make_test_finder()
        with self._basic_resolver(finder) as resolver:
            ireq_url = data.packages.joinpath("FSPkg").as_uri()
            ireq = get_processed_req_from_line(f"-e {ireq_url}#egg=FSPkg")
            reqset = resolver.resolve([ireq], True)
            assert len(reqset.all_requirements) == 1
            req = reqset.all_requirements[0]
            assert req.download_info
            assert req.download_info.url.startswith("file://")
            assert isinstance(req.download_info.info, DirInfo)
            assert req.download_info.info.editable

    @pytest.mark.network
    def test_download_info_vcs(self) -> None:
        """Test that download_info is set for requirements from git."""
        finder = make_test_finder()
        with self._basic_resolver(finder) as resolver:
            ireq = get_processed_req_from_line(
                "pip-test-package @ git+https://github.com/pypa/pip-test-package"
            )
            reqset = resolver.resolve([ireq], True)
            assert len(reqset.all_requirements) == 1
            req = reqset.all_requirements[0]
            assert req.download_info
            assert isinstance(req.download_info.info, VcsInfo)
            assert req.download_info.url == "https://github.com/pypa/pip-test-package"
            assert req.download_info.info.vcs == "git"


class TestInstallRequirement:
    def setup_method(self) -> None:
        self.tempdir = tempfile.mkdtemp()

    def teardown_method(self) -> None:
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_url_with_query(self) -> None:
        """InstallRequirement should strip the fragment, but not the query."""
        url = "http://foo.com/?p=bar.git;a=snapshot;h=v0.1;sf=tgz"
        fragment = "#egg=bar"
        req = install_req_from_line(url + fragment)
        assert req.link is not None
        assert req.link.url == url + fragment, req.link

    def test_pep440_wheel_link_requirement(self) -> None:
        url = "https://whatever.com/test-0.4-py2.py3-bogus-any.whl"
        line = "test @ https://whatever.com/test-0.4-py2.py3-bogus-any.whl"
        req = install_req_from_line(line)
        parts = str(req.req).split("@", 1)
        assert len(parts) == 2
        assert parts[0].strip() == "test"
        assert parts[1].strip() == url

    def test_pep440_url_link_requirement(self) -> None:
        url = "git+http://foo.com@ref#egg=foo"
        line = "foo @ git+http://foo.com@ref#egg=foo"
        req = install_req_from_line(line)
        parts = str(req.req).split("@", 1)
        assert len(parts) == 2
        assert parts[0].strip() == "foo"
        assert parts[1].strip() == url

    def test_url_with_authentication_link_requirement(self) -> None:
        url = "https://what@whatever.com/test-0.4-py2.py3-bogus-any.whl"
        line = "https://what@whatever.com/test-0.4-py2.py3-bogus-any.whl"
        req = install_req_from_line(line)
        assert req.link is not None
        assert req.link.is_wheel
        assert req.link.scheme == "https"
        assert req.link.url == url

    def test_str(self) -> None:
        req = install_req_from_line("simple==0.1")
        assert str(req) == "simple==0.1"

    def test_repr(self) -> None:
        req = install_req_from_line("simple==0.1")
        assert repr(req) == ("<InstallRequirement object: simple==0.1 editable=False>")

    def test_invalid_wheel_requirement_raises(self) -> None:
        with pytest.raises(InvalidWheelFilename):
            install_req_from_line("invalid.whl")

    def test_wheel_requirement_sets_req_attribute(self) -> None:
        req = install_req_from_line("simple-0.1-py2.py3-none-any.whl")
        assert isinstance(req.req, Requirement)
        assert str(req.req) == "simple==0.1"

    def test_url_preserved_line_req(self) -> None:
        """Confirm the url is preserved in a non-editable requirement"""
        url = "git+http://foo.com@ref#egg=foo"
        req = install_req_from_line(url)
        assert req.link is not None
        assert req.link.url == url

    def test_url_preserved_editable_req(self) -> None:
        """Confirm the url is preserved in a editable requirement"""
        url = "git+http://foo.com@ref#egg=foo"
        req = install_req_from_editable(url)
        assert req.link is not None
        assert req.link.url == url

    def test_markers(self) -> None:
        for line in (
            # recommended syntax
            'mock3; python_version >= "3"',
            # with more spaces
            'mock3 ; python_version >= "3" ',
            # without spaces
            'mock3;python_version >= "3"',
        ):
            req = install_req_from_line(line)
            assert req.req is not None
            assert req.req.name == "mock3"
            assert str(req.req.specifier) == ""
            assert str(req.markers) == 'python_version >= "3"'

    def test_markers_semicolon(self) -> None:
        # check that the markers can contain a semicolon
        req = install_req_from_line('semicolon; os_name == "a; b"')
        assert req.req is not None
        assert req.req.name == "semicolon"
        assert str(req.req.specifier) == ""
        assert str(req.markers) == 'os_name == "a; b"'

    def test_markers_url(self) -> None:
        # test "URL; markers" syntax
        url = "http://foo.com/?p=bar.git;a=snapshot;h=v0.1;sf=tgz"
        line = f'{url}; python_version >= "3"'
        req = install_req_from_line(line)
        assert req.link is not None
        assert req.link.url == url, req.link.url
        assert str(req.markers) == 'python_version >= "3"'

        # without space, markers are part of the URL
        url = "http://foo.com/?p=bar.git;a=snapshot;h=v0.1;sf=tgz"
        line = f'{url};python_version >= "3"'
        req = install_req_from_line(line)
        assert req.link is not None
        assert req.link.url == line, req.link.url
        assert req.markers is None

    def test_markers_match_from_line(self) -> None:
        # match
        for markers in (
            'python_version >= "1.0"',
            f"sys_platform == {sys.platform!r}",
        ):
            line = "name; " + markers
            req = install_req_from_line(line)
            assert str(req.markers) == str(Marker(markers))
            assert req.match_markers()

        # don't match
        for markers in (
            'python_version >= "5.0"',
            f"sys_platform != {sys.platform!r}",
        ):
            line = "name; " + markers
            req = install_req_from_line(line)
            assert str(req.markers) == str(Marker(markers))
            assert not req.match_markers()

    def test_markers_match(self) -> None:
        # match
        for markers in (
            'python_version >= "1.0"',
            f"sys_platform == {sys.platform!r}",
        ):
            line = "name; " + markers
            req = install_req_from_line(line, comes_from="")
            assert str(req.markers) == str(Marker(markers))
            assert req.match_markers()

        # don't match
        for markers in (
            'python_version >= "5.0"',
            f"sys_platform != {sys.platform!r}",
        ):
            line = "name; " + markers
            req = install_req_from_line(line, comes_from="")
            assert str(req.markers) == str(Marker(markers))
            assert not req.match_markers()

    def test_extras_for_line_path_requirement(self) -> None:
        line = "SomeProject[ex1,ex2]"
        filename = "filename"
        comes_from = f"-r {filename} (line 1)"
        req = install_req_from_line(line, comes_from=comes_from)
        assert len(req.extras) == 2
        assert req.extras == {"ex1", "ex2"}

    def test_extras_for_line_url_requirement(self) -> None:
        line = "git+https://url#egg=SomeProject[ex1,ex2]"
        filename = "filename"
        comes_from = f"-r {filename} (line 1)"
        req = install_req_from_line(line, comes_from=comes_from)
        assert len(req.extras) == 2
        assert req.extras == {"ex1", "ex2"}

    def test_extras_for_editable_path_requirement(self) -> None:
        url = ".[ex1,ex2]"
        filename = "filename"
        comes_from = f"-r {filename} (line 1)"
        req = install_req_from_editable(url, comes_from=comes_from)
        assert len(req.extras) == 2
        assert req.extras == {"ex1", "ex2"}

    def test_extras_for_editable_url_requirement(self) -> None:
        url = "git+https://url#egg=SomeProject[ex1,ex2]"
        filename = "filename"
        comes_from = f"-r {filename} (line 1)"
        req = install_req_from_editable(url, comes_from=comes_from)
        assert len(req.extras) == 2
        assert req.extras == {"ex1", "ex2"}

    def test_unexisting_path(self) -> None:
        with pytest.raises(InstallationError) as e:
            install_req_from_line(os.path.join("this", "path", "does", "not", "exist"))
        err_msg = e.value.args[0]
        assert "Invalid requirement" in err_msg
        assert "It looks like a path." in err_msg

    def test_single_equal_sign(self) -> None:
        with pytest.raises(InstallationError) as e:
            install_req_from_line("toto=42")
        err_msg = e.value.args[0]
        assert "Invalid requirement" in err_msg
        assert "= is not a valid operator. Did you mean == ?" in err_msg

    def test_unidentifiable_name(self) -> None:
        test_name = "-"
        with pytest.raises(InstallationError) as e:
            install_req_from_line(test_name)
        err_msg = e.value.args[0]
        assert f"Invalid requirement: '{test_name}'" == err_msg

    def test_requirement_file(self) -> None:
        req_file_path = os.path.join(self.tempdir, "test.txt")
        with open(req_file_path, "w") as req_file:
            req_file.write("pip\nsetuptools")
        with pytest.raises(InstallationError) as e:
            install_req_from_line(req_file_path)
        err_msg = e.value.args[0]
        assert "Invalid requirement" in err_msg
        assert "It looks like a path. The path does exist." in err_msg
        assert "appears to be a requirements file." in err_msg
        assert "If that is the case, use the '-r' flag to install" in err_msg


@mock.patch("pip._internal.req.req_install.os.path.abspath")
@mock.patch("pip._internal.req.req_install.os.path.exists")
@mock.patch("pip._internal.req.req_install.os.path.isdir")
def test_parse_editable_local(
    isdir_mock: mock.Mock, exists_mock: mock.Mock, abspath_mock: mock.Mock
) -> None:
    exists_mock.return_value = isdir_mock.return_value = True
    # mocks needed to support path operations on windows tests
    abspath_mock.return_value = "/some/path"
    assert parse_editable(".") == (None, "file:///some/path", set())
    abspath_mock.return_value = "/some/path/foo"
    assert parse_editable("foo") == (
        None,
        "file:///some/path/foo",
        set(),
    )


def test_parse_editable_explicit_vcs() -> None:
    assert parse_editable("svn+https://foo#egg=foo") == (
        "foo",
        "svn+https://foo#egg=foo",
        set(),
    )


def test_parse_editable_vcs_extras() -> None:
    assert parse_editable("svn+https://foo#egg=foo[extras]") == (
        "foo[extras]",
        "svn+https://foo#egg=foo[extras]",
        set(),
    )


@mock.patch("pip._internal.req.req_install.os.path.abspath")
@mock.patch("pip._internal.req.req_install.os.path.exists")
@mock.patch("pip._internal.req.req_install.os.path.isdir")
def test_parse_editable_local_extras(
    isdir_mock: mock.Mock, exists_mock: mock.Mock, abspath_mock: mock.Mock
) -> None:
    exists_mock.return_value = isdir_mock.return_value = True
    abspath_mock.return_value = "/some/path"
    assert parse_editable(".[extras]") == (
        None,
        "file:///some/path",
        {"extras"},
    )
    abspath_mock.return_value = "/some/path/foo"
    assert parse_editable("foo[bar,baz]") == (
        None,
        "file:///some/path/foo",
        {"bar", "baz"},
    )


def test_mismatched_versions(caplog: pytest.LogCaptureFixture) -> None:
    req = InstallRequirement(
        req=Requirement("simplewheel==2.0"),
        comes_from=None,
    )
    req.source_dir = "/tmp/somewhere"  # make req believe it has been unpacked
    # Monkeypatch!
    metadata = email.message.Message()
    metadata["name"] = "simplewheel"
    metadata["version"] = "1.0"
    req._metadata = metadata

    req.assert_source_matches_version()
    assert caplog.records[-1].message == (
        "Requested simplewheel==2.0, but installing version 1.0"
    )


@pytest.mark.parametrize(
    "args, expected",
    [
        # Test UNIX-like paths
        (("/path/to/installable"), True),
        # Test relative paths
        (("./path/to/installable"), True),
        # Test current path
        (("."), True),
        # Test url paths
        (("https://whatever.com/test-0.4-py2.py3-bogus-any.whl"), True),
        # Test pep440 paths
        (("test @ https://whatever.com/test-0.4-py2.py3-bogus-any.whl"), True),
        # Test wheel
        (("simple-0.1-py2.py3-none-any.whl"), False),
    ],
)
def test_looks_like_path(args: str, expected: bool) -> None:
    assert _looks_like_path(args) == expected


@pytest.mark.skipif(
    not sys.platform.startswith("win"), reason="Test only available on Windows"
)
@pytest.mark.parametrize(
    "args, expected",
    [
        # Test relative paths
        ((".\\path\\to\\installable"), True),
        (("relative\\path"), True),
        # Test absolute paths
        (("C:\\absolute\\path"), True),
    ],
)
def test_looks_like_path_win(args: str, expected: bool) -> None:
    assert _looks_like_path(args) == expected


@pytest.mark.parametrize(
    "args, mock_returns, expected",
    [
        # Test pep440 urls
        (
            (
                "/path/to/foo @ git+http://foo.com@ref#egg=foo",
                "foo @ git+http://foo.com@ref#egg=foo",
            ),
            (False, False),
            None,
        ),
        # Test pep440 urls without spaces
        (
            (
                "/path/to/foo@git+http://foo.com@ref#egg=foo",
                "foo @ git+http://foo.com@ref#egg=foo",
            ),
            (False, False),
            None,
        ),
        # Test pep440 wheel
        (
            (
                "/path/to/test @ https://whatever.com/test-0.4-py2.py3-bogus-any.whl",
                "test @ https://whatever.com/test-0.4-py2.py3-bogus-any.whl",
            ),
            (False, False),
            None,
        ),
        # Test name is not a file
        (("/path/to/simple==0.1", "simple==0.1"), (False, False), None),
    ],
)
@mock.patch("pip._internal.req.req_install.os.path.isdir")
@mock.patch("pip._internal.req.req_install.os.path.isfile")
def test_get_url_from_path(
    isdir_mock: mock.Mock,
    isfile_mock: mock.Mock,
    args: Tuple[str, str],
    mock_returns: Tuple[bool, bool],
    expected: None,
) -> None:
    isdir_mock.return_value = mock_returns[0]
    isfile_mock.return_value = mock_returns[1]
    assert _get_url_from_path(*args) is expected


@mock.patch("pip._internal.req.req_install.os.path.isdir")
@mock.patch("pip._internal.req.req_install.os.path.isfile")
def test_get_url_from_path__archive_file(
    isdir_mock: mock.Mock, isfile_mock: mock.Mock
) -> None:
    isdir_mock.return_value = False
    isfile_mock.return_value = True
    name = "simple-0.1-py2.py3-none-any.whl"
    url = Path(f"/path/to/{name}").resolve(strict=False).as_uri()
    assert _get_url_from_path(f"/path/to/{name}", name) == url


@mock.patch("pip._internal.req.req_install.os.path.isdir")
@mock.patch("pip._internal.req.req_install.os.path.isfile")
def test_get_url_from_path__installable_dir(
    isdir_mock: mock.Mock, isfile_mock: mock.Mock
) -> None:
    isdir_mock.return_value = True
    isfile_mock.return_value = True
    name = "some/setuptools/project"
    url = Path(f"/path/to/{name}").resolve(strict=False).as_uri()
    assert _get_url_from_path(f"/path/to/{name}", name) == url


@mock.patch("pip._internal.req.req_install.os.path.isdir")
def test_get_url_from_path__installable_error(isdir_mock: mock.Mock) -> None:
    isdir_mock.return_value = True
    name = "some/setuptools/project"
    path = os.path.join("/path/to/" + name)
    with pytest.raises(InstallationError) as e:
        _get_url_from_path(path, name)
    err_msg = e.value.args[0]
    assert "Neither 'setup.py' nor 'pyproject.toml' found" in err_msg
