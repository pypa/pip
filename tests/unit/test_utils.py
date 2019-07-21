# -*- coding: utf-8 -*-

"""
util tests

"""
import codecs
import itertools
import locale
import os
import shutil
import stat
import sys
import tempfile
import time
import warnings
from io import BytesIO
from logging import DEBUG, ERROR, INFO, WARNING
from textwrap import dedent

import pytest
from mock import Mock, patch
from pip._vendor.six.moves.urllib import request as urllib_request

from pip._internal.exceptions import (
    HashMismatch, HashMissing, InstallationError,
)
from pip._internal.utils.deprecation import PipDeprecationWarning, deprecated
from pip._internal.utils.encoding import BOMS, auto_decode
from pip._internal.utils.glibc import (
    check_glibc_version, glibc_version_string, glibc_version_string_confstr,
    glibc_version_string_ctypes,
)
from pip._internal.utils.hashes import Hashes, MissingHashes
from pip._internal.utils.misc import (
    call_subprocess, egg_link_path, ensure_dir, format_command_args,
    get_installed_distributions, get_prog, make_subprocess_output_error,
    normalize_path, normalize_version_info, path_to_display, path_to_url,
    redact_netloc, redact_password_from_url, remove_auth_from_url, rmtree,
    split_auth_from_netloc, split_auth_netloc_from_url, untar_file, unzip_file,
)
from pip._internal.utils.setuptools_build import make_setuptools_shim_args
from pip._internal.utils.temp_dir import AdjacentTempDirectory, TempDirectory
from pip._internal.utils.ui import SpinnerInterface


class Tests_EgglinkPath:
    "util.egg_link_path() tests"

    def setup(self):

        project = 'foo'

        self.mock_dist = Mock(project_name=project)
        self.site_packages = 'SITE_PACKAGES'
        self.user_site = 'USER_SITE'
        self.user_site_egglink = os.path.join(
            self.user_site,
            '%s.egg-link' % project
        )
        self.site_packages_egglink = os.path.join(
            self.site_packages,
            '%s.egg-link' % project,
        )

        # patches
        from pip._internal.utils import misc as utils
        self.old_site_packages = utils.site_packages
        self.mock_site_packages = utils.site_packages = 'SITE_PACKAGES'
        self.old_running_under_virtualenv = utils.running_under_virtualenv
        self.mock_running_under_virtualenv = utils.running_under_virtualenv = \
            Mock()
        self.old_virtualenv_no_global = utils.virtualenv_no_global
        self.mock_virtualenv_no_global = utils.virtualenv_no_global = Mock()
        self.old_user_site = utils.user_site
        self.mock_user_site = utils.user_site = self.user_site
        from os import path
        self.old_isfile = path.isfile
        self.mock_isfile = path.isfile = Mock()

    def teardown(self):
        from pip._internal.utils import misc as utils
        utils.site_packages = self.old_site_packages
        utils.running_under_virtualenv = self.old_running_under_virtualenv
        utils.virtualenv_no_global = self.old_virtualenv_no_global
        utils.user_site = self.old_user_site
        from os import path
        path.isfile = self.old_isfile

    def eggLinkInUserSite(self, egglink):
        return egglink == self.user_site_egglink

    def eggLinkInSitePackages(self, egglink):
        return egglink == self.site_packages_egglink

    # ####################### #
    # # egglink in usersite # #
    # ####################### #
    def test_egglink_in_usersite_notvenv(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = False
        self.mock_isfile.side_effect = self.eggLinkInUserSite
        assert egg_link_path(self.mock_dist) == self.user_site_egglink

    def test_egglink_in_usersite_venv_noglobal(self):
        self.mock_virtualenv_no_global.return_value = True
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.side_effect = self.eggLinkInUserSite
        assert egg_link_path(self.mock_dist) is None

    def test_egglink_in_usersite_venv_global(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.side_effect = self.eggLinkInUserSite
        assert egg_link_path(self.mock_dist) == self.user_site_egglink

    # ####################### #
    # # egglink in sitepkgs # #
    # ####################### #
    def test_egglink_in_sitepkgs_notvenv(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = False
        self.mock_isfile.side_effect = self.eggLinkInSitePackages
        assert egg_link_path(self.mock_dist) == self.site_packages_egglink

    def test_egglink_in_sitepkgs_venv_noglobal(self):
        self.mock_virtualenv_no_global.return_value = True
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.side_effect = self.eggLinkInSitePackages
        assert egg_link_path(self.mock_dist) == self.site_packages_egglink

    def test_egglink_in_sitepkgs_venv_global(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.side_effect = self.eggLinkInSitePackages
        assert egg_link_path(self.mock_dist) == self.site_packages_egglink

    # ################################## #
    # # egglink in usersite & sitepkgs # #
    # ################################## #
    def test_egglink_in_both_notvenv(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = False
        self.mock_isfile.return_value = True
        assert egg_link_path(self.mock_dist) == self.user_site_egglink

    def test_egglink_in_both_venv_noglobal(self):
        self.mock_virtualenv_no_global.return_value = True
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.return_value = True
        assert egg_link_path(self.mock_dist) == self.site_packages_egglink

    def test_egglink_in_both_venv_global(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.return_value = True
        assert egg_link_path(self.mock_dist) == self.site_packages_egglink

    # ############## #
    # # no egglink # #
    # ############## #
    def test_noegglink_in_sitepkgs_notvenv(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = False
        self.mock_isfile.return_value = False
        assert egg_link_path(self.mock_dist) is None

    def test_noegglink_in_sitepkgs_venv_noglobal(self):
        self.mock_virtualenv_no_global.return_value = True
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.return_value = False
        assert egg_link_path(self.mock_dist) is None

    def test_noegglink_in_sitepkgs_venv_global(self):
        self.mock_virtualenv_no_global.return_value = False
        self.mock_running_under_virtualenv.return_value = True
        self.mock_isfile.return_value = False
        assert egg_link_path(self.mock_dist) is None


@patch('pip._internal.utils.misc.dist_in_usersite')
@patch('pip._internal.utils.misc.dist_is_local')
@patch('pip._internal.utils.misc.dist_is_editable')
class Tests_get_installed_distributions:
    """test util.get_installed_distributions"""

    workingset = [
        Mock(test_name="global"),
        Mock(test_name="editable"),
        Mock(test_name="normal"),
        Mock(test_name="user"),
    ]

    workingset_stdlib = [
        Mock(test_name='normal', key='argparse'),
        Mock(test_name='normal', key='wsgiref')
    ]

    workingset_freeze = [
        Mock(test_name='normal', key='pip'),
        Mock(test_name='normal', key='setuptools'),
        Mock(test_name='normal', key='distribute')
    ]

    def dist_is_editable(self, dist):
        return dist.test_name == "editable"

    def dist_is_local(self, dist):
        return dist.test_name != "global" and dist.test_name != 'user'

    def dist_in_usersite(self, dist):
        return dist.test_name == "user"

    @patch('pip._vendor.pkg_resources.working_set', workingset)
    def test_editables_only(self, mock_dist_is_editable,
                            mock_dist_is_local,
                            mock_dist_in_usersite):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        mock_dist_in_usersite.side_effect = self.dist_in_usersite
        dists = get_installed_distributions(editables_only=True)
        assert len(dists) == 1, dists
        assert dists[0].test_name == "editable"

    @patch('pip._vendor.pkg_resources.working_set', workingset)
    def test_exclude_editables(self, mock_dist_is_editable,
                               mock_dist_is_local,
                               mock_dist_in_usersite):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        mock_dist_in_usersite.side_effect = self.dist_in_usersite
        dists = get_installed_distributions(include_editables=False)
        assert len(dists) == 1
        assert dists[0].test_name == "normal"

    @patch('pip._vendor.pkg_resources.working_set', workingset)
    def test_include_globals(self, mock_dist_is_editable,
                             mock_dist_is_local,
                             mock_dist_in_usersite):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        mock_dist_in_usersite.side_effect = self.dist_in_usersite
        dists = get_installed_distributions(local_only=False)
        assert len(dists) == 4

    @patch('pip._vendor.pkg_resources.working_set', workingset)
    def test_user_only(self, mock_dist_is_editable,
                       mock_dist_is_local,
                       mock_dist_in_usersite):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        mock_dist_in_usersite.side_effect = self.dist_in_usersite
        dists = get_installed_distributions(local_only=False,
                                            user_only=True)
        assert len(dists) == 1
        assert dists[0].test_name == "user"

    @patch('pip._vendor.pkg_resources.working_set', workingset_stdlib)
    def test_gte_py27_excludes(self, mock_dist_is_editable,
                               mock_dist_is_local,
                               mock_dist_in_usersite):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        mock_dist_in_usersite.side_effect = self.dist_in_usersite
        dists = get_installed_distributions()
        assert len(dists) == 0

    @patch('pip._vendor.pkg_resources.working_set', workingset_freeze)
    def test_freeze_excludes(self, mock_dist_is_editable,
                             mock_dist_is_local,
                             mock_dist_in_usersite):
        mock_dist_is_editable.side_effect = self.dist_is_editable
        mock_dist_is_local.side_effect = self.dist_is_local
        mock_dist_in_usersite.side_effect = self.dist_in_usersite
        dists = get_installed_distributions(
            skip=('setuptools', 'pip', 'distribute'))
        assert len(dists) == 0


class TestUnpackArchives(object):
    """
    test_tar.tgz/test_tar.zip have content as follows engineered to confirm 3
    things:
     1) confirm that reg files, dirs, and symlinks get unpacked
     2) permissions are not preserved (and go by the 022 umask)
     3) reg files with *any* execute perms, get chmod +x

       file.txt         600 regular file
       symlink.txt      777 symlink to file.txt
       script_owner.sh  700 script where owner can execute
       script_group.sh  610 script where group can execute
       script_world.sh  601 script where world can execute
       dir              744 directory
       dir/dirfile      622 regular file
     4) the file contents are extracted correctly (though the content of
        each file isn't currently unique)

    """

    def setup(self):
        self.tempdir = tempfile.mkdtemp()
        self.old_mask = os.umask(0o022)
        self.symlink_expected_mode = None

    def teardown(self):
        os.umask(self.old_mask)
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def mode(self, path):
        return stat.S_IMODE(os.stat(path).st_mode)

    def confirm_files(self):
        # expectations based on 022 umask set above and the unpack logic that
        # sets execute permissions, not preservation
        for fname, expected_mode, test, expected_contents in [
                ('file.txt', 0o644, os.path.isfile, b'file\n'),
                # We don't test the "symlink.txt" contents for now.
                ('symlink.txt', 0o644, os.path.isfile, None),
                ('script_owner.sh', 0o755, os.path.isfile, b'file\n'),
                ('script_group.sh', 0o755, os.path.isfile, b'file\n'),
                ('script_world.sh', 0o755, os.path.isfile, b'file\n'),
                ('dir', 0o755, os.path.isdir, None),
                (os.path.join('dir', 'dirfile'), 0o644, os.path.isfile, b''),
        ]:
            path = os.path.join(self.tempdir, fname)
            if path.endswith('symlink.txt') and sys.platform == 'win32':
                # no symlinks created on windows
                continue
            assert test(path), path
            if expected_contents is not None:
                with open(path, mode='rb') as f:
                    contents = f.read()
                assert contents == expected_contents, 'fname: {}'.format(fname)
            if sys.platform == 'win32':
                # the permissions tests below don't apply in windows
                # due to os.chmod being a noop
                continue
            mode = self.mode(path)
            assert mode == expected_mode, (
                "mode: %s, expected mode: %s" % (mode, expected_mode)
            )

    def test_unpack_tgz(self, data):
        """
        Test unpacking a *.tgz, and setting execute permissions
        """
        test_file = data.packages.joinpath("test_tar.tgz")
        untar_file(test_file, self.tempdir)
        self.confirm_files()
        # Check the timestamp of an extracted file
        file_txt_path = os.path.join(self.tempdir, 'file.txt')
        mtime = time.gmtime(os.stat(file_txt_path).st_mtime)
        assert mtime[0:6] == (2013, 8, 16, 5, 13, 37), mtime

    def test_unpack_zip(self, data):
        """
        Test unpacking a *.zip, and setting execute permissions
        """
        test_file = data.packages.joinpath("test_zip.zip")
        unzip_file(test_file, self.tempdir)
        self.confirm_files()


class Failer:
    def __init__(self, duration=1):
        self.succeed_after = time.time() + duration

    def call(self, *args, **kw):
        """Fail with OSError self.max_fails times"""
        if time.time() < self.succeed_after:
            raise OSError("Failed")


def test_rmtree_retries(tmpdir, monkeypatch):
    """
    Test pip._internal.utils.rmtree will retry failures
    """
    monkeypatch.setattr(shutil, 'rmtree', Failer(duration=1).call)
    rmtree('foo')


def test_rmtree_retries_for_3sec(tmpdir, monkeypatch):
    """
    Test pip._internal.utils.rmtree will retry failures for no more than 3 sec
    """
    monkeypatch.setattr(shutil, 'rmtree', Failer(duration=5).call)
    with pytest.raises(OSError):
        rmtree('foo')


@pytest.mark.parametrize('path, fs_encoding, expected', [
    (None, None, None),
    # Test passing a text (unicode) string.
    (u'/path/déf', None, u'/path/déf'),
    # Test a bytes object with a non-ascii character.
    (u'/path/déf'.encode('utf-8'), 'utf-8', u'/path/déf'),
    # Test a bytes object with a character that can't be decoded.
    (u'/path/déf'.encode('utf-8'), 'ascii', u"b'/path/d\\xc3\\xa9f'"),
    (u'/path/déf'.encode('utf-16'), 'utf-8',
     u"b'\\xff\\xfe/\\x00p\\x00a\\x00t\\x00h\\x00/"
     "\\x00d\\x00\\xe9\\x00f\\x00'"),
])
def test_path_to_display(monkeypatch, path, fs_encoding, expected):
    monkeypatch.setattr(sys, 'getfilesystemencoding', lambda: fs_encoding)
    actual = path_to_display(path)
    assert actual == expected, 'actual: {!r}'.format(actual)


class Test_normalize_path(object):
    # Technically, symlinks are possible on Windows, but you need a special
    # permission bit to create them, and Python 2 doesn't support it anyway, so
    # it's easiest just to skip this test on Windows altogether.
    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_resolve_symlinks(self, tmpdir):
        print(type(tmpdir))
        print(dir(tmpdir))
        orig_working_dir = os.getcwd()
        os.chdir(tmpdir)
        try:
            d = os.path.join('foo', 'bar')
            f = os.path.join(d, 'file1')
            os.makedirs(d)
            with open(f, 'w'):  # Create the file
                pass

            os.symlink(d, 'dir_link')
            os.symlink(f, 'file_link')

            assert normalize_path(
                'dir_link/file1', resolve_symlinks=True
            ) == os.path.join(tmpdir, f)
            assert normalize_path(
                'dir_link/file1', resolve_symlinks=False
            ) == os.path.join(tmpdir, 'dir_link', 'file1')

            assert normalize_path(
                'file_link', resolve_symlinks=True
            ) == os.path.join(tmpdir, f)
            assert normalize_path(
                'file_link', resolve_symlinks=False
            ) == os.path.join(tmpdir, 'file_link')
        finally:
            os.chdir(orig_working_dir)


class TestHashes(object):
    """Tests for pip._internal.utils.hashes"""

    @pytest.mark.parametrize('hash_name, hex_digest, expected', [
        # Test a value that matches but with the wrong hash_name.
        ('sha384', 128 * 'a', False),
        # Test matching values, including values other than the first.
        ('sha512', 128 * 'a', True),
        ('sha512', 128 * 'b', True),
        # Test a matching hash_name with a value that doesn't match.
        ('sha512', 128 * 'c', False),
    ])
    def test_is_hash_allowed(self, hash_name, hex_digest, expected):
        hashes_data = {
            'sha512': [128 * 'a', 128 * 'b'],
        }
        hashes = Hashes(hashes_data)
        assert hashes.is_hash_allowed(hash_name, hex_digest) == expected

    def test_success(self, tmpdir):
        """Make sure no error is raised when at least one hash matches.

        Test check_against_path because it calls everything else.

        """
        file = tmpdir / 'to_hash'
        file.write_text('hello')
        hashes = Hashes({
            'sha256': ['2cf24dba5fb0a30e26e83b2ac5b9e29e'
                       '1b161e5c1fa7425e73043362938b9824'],
            'sha224': ['wrongwrong'],
            'md5': ['5d41402abc4b2a76b9719d911017c592']})
        hashes.check_against_path(file)

    def test_failure(self):
        """Hashes should raise HashMismatch when no hashes match."""
        hashes = Hashes({'sha256': ['wrongwrong']})
        with pytest.raises(HashMismatch):
            hashes.check_against_file(BytesIO(b'hello'))

    def test_missing_hashes(self):
        """MissingHashes should raise HashMissing when any check is done."""
        with pytest.raises(HashMissing):
            MissingHashes().check_against_file(BytesIO(b'hello'))

    def test_unknown_hash(self):
        """Hashes should raise InstallationError when it encounters an unknown
        hash."""
        hashes = Hashes({'badbad': ['dummy']})
        with pytest.raises(InstallationError):
            hashes.check_against_file(BytesIO(b'hello'))

    def test_non_zero(self):
        """Test that truthiness tests tell whether any known-good hashes
        exist."""
        assert Hashes({'sha256': 'dummy'})
        assert not Hashes()
        assert not Hashes({})


class TestEncoding(object):
    """Tests for pip._internal.utils.encoding"""

    def test_auto_decode_utf_16_le(self):
        data = (
            b'\xff\xfeD\x00j\x00a\x00n\x00g\x00o\x00=\x00'
            b'=\x001\x00.\x004\x00.\x002\x00'
        )
        assert data.startswith(codecs.BOM_UTF16_LE)
        assert auto_decode(data) == "Django==1.4.2"

    def test_auto_decode_utf_16_be(self):
        data = (
            b'\xfe\xff\x00D\x00j\x00a\x00n\x00g\x00o\x00='
            b'\x00=\x001\x00.\x004\x00.\x002'
        )
        assert data.startswith(codecs.BOM_UTF16_BE)
        assert auto_decode(data) == "Django==1.4.2"

    def test_auto_decode_no_bom(self):
        assert auto_decode(b'foobar') == u'foobar'

    def test_auto_decode_pep263_headers(self):
        latin1_req = u'# coding=latin1\n# Pas trop de café'
        assert auto_decode(latin1_req.encode('latin1')) == latin1_req

    def test_auto_decode_no_preferred_encoding(self):
        om, em = Mock(), Mock()
        om.return_value = 'ascii'
        em.return_value = None
        data = u'data'
        with patch('sys.getdefaultencoding', om):
            with patch('locale.getpreferredencoding', em):
                ret = auto_decode(data.encode(sys.getdefaultencoding()))
        assert ret == data

    @pytest.mark.parametrize('encoding', [encoding for bom, encoding in BOMS])
    def test_all_encodings_are_valid(self, encoding):
        # we really only care that there is no LookupError
        assert ''.encode(encoding).decode(encoding) == ''


class TestTempDirectory(object):

    # No need to test symlinked directories on Windows
    @pytest.mark.skipif("sys.platform == 'win32'")
    def test_symlinked_path(self):
        with TempDirectory() as tmp_dir:
            assert os.path.exists(tmp_dir.path)

            alt_tmp_dir = tempfile.mkdtemp(prefix="pip-test-")
            assert (
                os.path.dirname(tmp_dir.path) ==
                os.path.dirname(os.path.realpath(alt_tmp_dir))
            )
            # are we on a system where /tmp is a symlink
            if os.path.realpath(alt_tmp_dir) != os.path.abspath(alt_tmp_dir):
                assert (
                    os.path.dirname(tmp_dir.path) !=
                    os.path.dirname(alt_tmp_dir)
                )
            else:
                assert (
                    os.path.dirname(tmp_dir.path) ==
                    os.path.dirname(alt_tmp_dir)
                )
            os.rmdir(tmp_dir.path)
            assert not os.path.exists(tmp_dir.path)

    def test_deletes_readonly_files(self):
        def create_file(*args):
            fpath = os.path.join(*args)
            ensure_dir(os.path.dirname(fpath))
            with open(fpath, "w") as f:
                f.write("Holla!")

        def readonly_file(*args):
            fpath = os.path.join(*args)
            os.chmod(fpath, stat.S_IREAD)

        with TempDirectory() as tmp_dir:
            create_file(tmp_dir.path, "normal-file")
            create_file(tmp_dir.path, "readonly-file")
            readonly_file(tmp_dir.path, "readonly-file")

            create_file(tmp_dir.path, "subfolder", "normal-file")
            create_file(tmp_dir.path, "subfolder", "readonly-file")
            readonly_file(tmp_dir.path, "subfolder", "readonly-file")

        assert tmp_dir.path is None

    def test_create_and_cleanup_work(self):
        tmp_dir = TempDirectory()
        assert tmp_dir.path is None

        tmp_dir.create()
        created_path = tmp_dir.path
        assert tmp_dir.path is not None
        assert os.path.exists(created_path)

        tmp_dir.cleanup()
        assert tmp_dir.path is None
        assert not os.path.exists(created_path)

    @pytest.mark.parametrize("name", [
        "ABC",
        "ABC.dist-info",
        "_+-",
        "_package",
        "A......B",
        "AB",
        "A",
        "2",
    ])
    def test_adjacent_directory_names(self, name):
        def names():
            return AdjacentTempDirectory._generate_names(name)

        chars = AdjacentTempDirectory.LEADING_CHARS

        # Ensure many names are unique
        # (For long *name*, this sequence can be extremely long.
        # However, since we're only ever going to take the first
        # result that works, provided there are many of those
        # and that shorter names result in totally unique sets,
        # it's okay to skip part of the test.)
        some_names = list(itertools.islice(names(), 1000))
        # We should always get at least 1000 names
        assert len(some_names) == 1000

        # Ensure original name does not appear early in the set
        assert name not in some_names

        if len(name) > 2:
            # Names should be at least 90% unique (given the infinite
            # range of inputs, and the possibility that generated names
            # may already exist on disk anyway, this is a much cheaper
            # criteria to enforce than complete uniqueness).
            assert len(some_names) > 0.9 * len(set(some_names))

            # Ensure the first few names are the same length as the original
            same_len = list(itertools.takewhile(
                lambda x: len(x) == len(name),
                some_names
            ))
            assert len(same_len) > 10

            # Check the first group are correct
            expected_names = ['~' + name[1:]]
            expected_names.extend('~' + c + name[2:] for c in chars)
            for x, y in zip(some_names, expected_names):
                assert x == y

        else:
            # All names are going to be longer than our original
            assert min(len(x) for x in some_names) > 1

            # All names are going to be unique
            assert len(some_names) == len(set(some_names))

            if len(name) == 2:
                # All but the first name are going to end with our original
                assert all(x.endswith(name) for x in some_names[1:])
            else:
                # All names are going to end with our original
                assert all(x.endswith(name) for x in some_names)

    @pytest.mark.parametrize("name", [
        "A",
        "ABC",
        "ABC.dist-info",
        "_+-",
        "_package",
    ])
    def test_adjacent_directory_exists(self, name, tmpdir):
        block_name, expect_name = itertools.islice(
            AdjacentTempDirectory._generate_names(name), 2)

        original = os.path.join(tmpdir, name)
        blocker = os.path.join(tmpdir, block_name)

        ensure_dir(original)
        ensure_dir(blocker)

        with AdjacentTempDirectory(original) as atmp_dir:
            assert expect_name == os.path.split(atmp_dir.path)[1]

    def test_adjacent_directory_permission_error(self, monkeypatch):
        name = "ABC"

        def raising_mkdir(*args, **kwargs):
            raise OSError("Unknown OSError")

        with TempDirectory() as tmp_dir:
            original = os.path.join(tmp_dir.path, name)

            ensure_dir(original)
            monkeypatch.setattr("os.mkdir", raising_mkdir)

            with pytest.raises(OSError):
                with AdjacentTempDirectory(original):
                    pass


def raises(error):
    raise error


class TestGlibc(object):
    def test_manylinux_check_glibc_version(self):
        """
        Test that the check_glibc_version function is robust against weird
        glibc version strings.
        """
        for two_twenty in ["2.20",
                           # used by "linaro glibc", see gh-3588
                           "2.20-2014.11",
                           # weird possibilities that I just made up
                           "2.20+dev",
                           "2.20-custom",
                           "2.20.1",
                           ]:
            assert check_glibc_version(two_twenty, 2, 15)
            assert check_glibc_version(two_twenty, 2, 20)
            assert not check_glibc_version(two_twenty, 2, 21)
            assert not check_glibc_version(two_twenty, 3, 15)
            assert not check_glibc_version(two_twenty, 1, 15)

        # For strings that we just can't parse at all, we should warn and
        # return false
        for bad_string in ["asdf", "", "foo.bar"]:
            with warnings.catch_warnings(record=True) as ws:
                warnings.filterwarnings("always")
                assert not check_glibc_version(bad_string, 2, 5)
                for w in ws:
                    if "Expected glibc version with" in str(w.message):
                        break
                else:
                    # Didn't find the warning we were expecting
                    assert False

    def test_glibc_version_string(self, monkeypatch):
        monkeypatch.setattr(
            os, "confstr", lambda x: "glibc 2.20", raising=False,
        )
        assert glibc_version_string() == "2.20"

    def test_glibc_version_string_confstr(self, monkeypatch):
        monkeypatch.setattr(
            os, "confstr", lambda x: "glibc 2.20", raising=False,
        )
        assert glibc_version_string_confstr() == "2.20"

    @pytest.mark.parametrize("failure", [
        lambda x: raises(ValueError),
        lambda x: raises(OSError),
        lambda x: "XXX",
    ])
    def test_glibc_version_string_confstr_fail(self, monkeypatch, failure):
        monkeypatch.setattr(os, "confstr", failure, raising=False)
        assert glibc_version_string_confstr() is None

    def test_glibc_version_string_confstr_missing(self, monkeypatch):
        monkeypatch.delattr(os, "confstr", raising=False)
        assert glibc_version_string_confstr() is None

    def test_glibc_version_string_ctypes_missing(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "ctypes", None)
        assert glibc_version_string_ctypes() is None


@pytest.mark.parametrize('version_info, expected', [
    ((), (0, 0, 0)),
    ((3, ), (3, 0, 0)),
    ((3, 6), (3, 6, 0)),
    ((3, 6, 2), (3, 6, 2)),
    ((3, 6, 2, 4), (3, 6, 2)),
])
def test_normalize_version_info(version_info, expected):
    actual = normalize_version_info(version_info)
    assert actual == expected


class TestGetProg(object):

    @pytest.mark.parametrize(
        ("argv", "executable", "expected"),
        [
            ('/usr/bin/pip', '', 'pip'),
            ('-c', '/usr/bin/python', '/usr/bin/python -m pip'),
            ('__main__.py', '/usr/bin/python', '/usr/bin/python -m pip'),
            ('/usr/bin/pip3', '', 'pip3'),
        ]
    )
    def test_get_prog(self, monkeypatch, argv, executable, expected):
        monkeypatch.setattr('pip._internal.utils.misc.sys.argv', [argv])
        monkeypatch.setattr(
            'pip._internal.utils.misc.sys.executable',
            executable
        )
        assert get_prog() == expected


@pytest.mark.parametrize('args, expected', [
    (['pip', 'list'], 'pip list'),
    (['foo', 'space space', 'new\nline', 'double"quote', "single'quote"],
     """foo 'space space' 'new\nline' 'double"quote' 'single'"'"'quote'"""),
])
def test_format_command_args(args, expected):
    actual = format_command_args(args)
    assert actual == expected


def test_make_subprocess_output_error():
    cmd_args = ['test', 'has space']
    cwd = '/path/to/cwd'
    lines = ['line1\n', 'line2\n', 'line3\n']
    actual = make_subprocess_output_error(
        cmd_args=cmd_args,
        cwd=cwd,
        lines=lines,
        exit_status=3,
    )
    expected = dedent("""\
    Command errored out with exit status 3:
     command: test 'has space'
         cwd: /path/to/cwd
    Complete output (3 lines):
    line1
    line2
    line3
    ----------------------------------------""")
    assert actual == expected, 'actual: {}'.format(actual)


def test_make_subprocess_output_error__non_ascii_command_arg(monkeypatch):
    """
    Test a command argument with a non-ascii character.
    """
    cmd_args = ['foo', 'déf']
    if sys.version_info[0] == 2:
        # Check in Python 2 that the str (bytes object) with the non-ascii
        # character has the encoding we expect. (This comes from the source
        # code encoding at the top of the file.)
        assert cmd_args[1].decode('utf-8') == u'déf'

    # We need to monkeypatch so the encoding will be correct on Windows.
    monkeypatch.setattr(locale, 'getpreferredencoding', lambda: 'utf-8')
    actual = make_subprocess_output_error(
        cmd_args=cmd_args,
        cwd='/path/to/cwd',
        lines=[],
        exit_status=1,
    )
    expected = dedent(u"""\
    Command errored out with exit status 1:
     command: foo 'déf'
         cwd: /path/to/cwd
    Complete output (0 lines):
    ----------------------------------------""")
    assert actual == expected, u'actual: {}'.format(actual)


@pytest.mark.skipif("sys.version_info < (3,)")
def test_make_subprocess_output_error__non_ascii_cwd_python_3(monkeypatch):
    """
    Test a str (text) cwd with a non-ascii character in Python 3.
    """
    cmd_args = ['test']
    cwd = '/path/to/cwd/déf'
    actual = make_subprocess_output_error(
        cmd_args=cmd_args,
        cwd=cwd,
        lines=[],
        exit_status=1,
    )
    expected = dedent("""\
    Command errored out with exit status 1:
     command: test
         cwd: /path/to/cwd/déf
    Complete output (0 lines):
    ----------------------------------------""")
    assert actual == expected, 'actual: {}'.format(actual)


@pytest.mark.parametrize('encoding', [
    'utf-8',
    # Test a Windows encoding.
    'cp1252',
])
@pytest.mark.skipif("sys.version_info >= (3,)")
def test_make_subprocess_output_error__non_ascii_cwd_python_2(
    monkeypatch, encoding,
):
    """
    Test a str (bytes object) cwd with a non-ascii character in Python 2.
    """
    cmd_args = ['test']
    cwd = u'/path/to/cwd/déf'.encode(encoding)
    monkeypatch.setattr(sys, 'getfilesystemencoding', lambda: encoding)
    actual = make_subprocess_output_error(
        cmd_args=cmd_args,
        cwd=cwd,
        lines=[],
        exit_status=1,
    )
    expected = dedent(u"""\
    Command errored out with exit status 1:
     command: test
         cwd: /path/to/cwd/déf
    Complete output (0 lines):
    ----------------------------------------""")
    assert actual == expected, u'actual: {}'.format(actual)


# This test is mainly important for checking unicode in Python 2.
def test_make_subprocess_output_error__non_ascii_line():
    """
    Test a line with a non-ascii character.
    """
    lines = [u'curly-quote: \u2018\n']
    actual = make_subprocess_output_error(
        cmd_args=['test'],
        cwd='/path/to/cwd',
        lines=lines,
        exit_status=1,
    )
    expected = dedent(u"""\
    Command errored out with exit status 1:
     command: test
         cwd: /path/to/cwd
    Complete output (1 lines):
    curly-quote: \u2018
    ----------------------------------------""")
    assert actual == expected, u'actual: {}'.format(actual)


class FakeSpinner(SpinnerInterface):

    def __init__(self):
        self.spin_count = 0
        self.final_status = None

    def spin(self):
        self.spin_count += 1

    def finish(self, final_status):
        self.final_status = final_status


class TestCallSubprocess(object):

    """
    Test call_subprocess().
    """

    def check_result(
        self, capfd, caplog, log_level, spinner, result, expected,
        expected_spinner,
    ):
        """
        Check the result of calling call_subprocess().

        :param log_level: the logging level that caplog was set to.
        :param spinner: the FakeSpinner object passed to call_subprocess()
            to be checked.
        :param result: the call_subprocess() return value to be checked.
        :param expected: a pair (expected_proc, expected_records), where
            1) `expected_proc` is the expected return value of
              call_subprocess() as a list of lines, or None if the return
              value is expected to be None;
            2) `expected_records` is the expected value of
              caplog.record_tuples.
        :param expected_spinner: a 2-tuple of the spinner's expected
            (spin_count, final_status).
        """
        expected_proc, expected_records = expected

        if expected_proc is None:
            assert result is None
        else:
            assert result.splitlines() == expected_proc

        # Confirm that stdout and stderr haven't been written to.
        captured = capfd.readouterr()
        assert (captured.out, captured.err) == ('', '')

        records = caplog.record_tuples
        if len(records) != len(expected_records):
            raise RuntimeError('{} != {}'.format(records, expected_records))

        for record, expected_record in zip(records, expected_records):
            # Check the logger_name and log level parts exactly.
            assert record[:2] == expected_record[:2]
            # For the message portion, check only a substring.  Also, we
            # can't use startswith() since the order of stdout and stderr
            # isn't guaranteed in cases where stderr is also present.
            # For example, we observed the stderr lines coming before stdout
            # in CI for PyPy 2.7 even though stdout happens first
            # chronologically.
            assert expected_record[2] in record[2]

        assert (spinner.spin_count, spinner.final_status) == expected_spinner

    def prepare_call(self, caplog, log_level, command=None):
        if command is None:
            command = 'print("Hello"); print("world")'

        caplog.set_level(log_level)
        spinner = FakeSpinner()
        args = [sys.executable, '-c', command]

        return (args, spinner)

    def test_debug_logging(self, capfd, caplog):
        """
        Test DEBUG logging (and without passing show_stdout=True).
        """
        log_level = DEBUG
        args, spinner = self.prepare_call(caplog, log_level)
        result = call_subprocess(args, spinner=spinner)

        expected = (['Hello', 'world'], [
            ('pip.subprocessor', DEBUG, 'Running command '),
            ('pip.subprocessor', DEBUG, 'Hello'),
            ('pip.subprocessor', DEBUG, 'world'),
        ])
        # The spinner shouldn't spin in this case since the subprocess
        # output is already being logged to the console.
        self.check_result(
            capfd, caplog, log_level, spinner, result, expected,
            expected_spinner=(0, None),
        )

    def test_info_logging(self, capfd, caplog):
        """
        Test INFO logging (and without passing show_stdout=True).
        """
        log_level = INFO
        args, spinner = self.prepare_call(caplog, log_level)
        result = call_subprocess(args, spinner=spinner)

        expected = (['Hello', 'world'], [])
        # The spinner should spin twice in this case since the subprocess
        # output isn't being written to the console.
        self.check_result(
            capfd, caplog, log_level, spinner, result, expected,
            expected_spinner=(2, 'done'),
        )

    def test_info_logging__subprocess_error(self, capfd, caplog):
        """
        Test INFO logging of a subprocess with an error (and without passing
        show_stdout=True).
        """
        log_level = INFO
        command = 'print("Hello"); print("world"); exit("fail")'
        args, spinner = self.prepare_call(caplog, log_level, command=command)

        with pytest.raises(InstallationError) as exc:
            call_subprocess(args, spinner=spinner)
        result = None
        exc_message = str(exc.value)
        assert exc_message.startswith(
            'Command errored out with exit status 1: '
        )
        assert exc_message.endswith('Check the logs for full command output.')

        expected = (None, [
            ('pip.subprocessor', ERROR, 'Complete output (3 lines):\n'),
        ])
        # The spinner should spin three times in this case since the
        # subprocess output isn't being written to the console.
        self.check_result(
            capfd, caplog, log_level, spinner, result, expected,
            expected_spinner=(3, 'error'),
        )

        # Do some further checking on the captured log records to confirm
        # that the subprocess output was logged.
        last_record = caplog.record_tuples[-1]
        last_message = last_record[2]
        lines = last_message.splitlines()

        # We have to sort before comparing the lines because we can't
        # guarantee the order in which stdout and stderr will appear.
        # For example, we observed the stderr lines coming before stdout
        # in CI for PyPy 2.7 even though stdout happens first chronologically.
        actual = sorted(lines)
        # Test the "command" line separately because we can't test an
        # exact match.
        command_line = actual.pop(1)
        assert actual == [
            '     cwd: None',
            '----------------------------------------',
            'Command errored out with exit status 1:',
            'Complete output (3 lines):',
            'Hello',
            'fail',
            'world',
        ], 'lines: {}'.format(actual)  # Show the full output on failure.

        assert command_line.startswith(' command: ')
        assert command_line.endswith('print("world"); exit("fail")\'')

    def test_info_logging_with_show_stdout_true(self, capfd, caplog):
        """
        Test INFO logging with show_stdout=True.
        """
        log_level = INFO
        args, spinner = self.prepare_call(caplog, log_level)
        result = call_subprocess(args, spinner=spinner, show_stdout=True)

        expected = (['Hello', 'world'], [
            ('pip.subprocessor', INFO, 'Running command '),
            ('pip.subprocessor', INFO, 'Hello'),
            ('pip.subprocessor', INFO, 'world'),
        ])
        # The spinner shouldn't spin in this case since the subprocess
        # output is already being written to the console.
        self.check_result(
            capfd, caplog, log_level, spinner, result, expected,
            expected_spinner=(0, None),
        )

    @pytest.mark.parametrize((
        'exit_status', 'show_stdout', 'extra_ok_returncodes', 'log_level',
        'expected'),
        [
            # The spinner should show here because show_stdout=False means
            # the subprocess should get logged at DEBUG level, but the passed
            # log level is only INFO.
            (0, False, None, INFO, (None, 'done', 2)),
            # Test some cases where the spinner should not be shown.
            (0, False, None, DEBUG, (None, None, 0)),
            # Test show_stdout=True.
            (0, True, None, DEBUG, (None, None, 0)),
            (0, True, None, INFO, (None, None, 0)),
            # The spinner should show here because show_stdout=True means
            # the subprocess should get logged at INFO level, but the passed
            # log level is only WARNING.
            (0, True, None, WARNING, (None, 'done', 2)),
            # Test a non-zero exit status.
            (3, False, None, INFO, (InstallationError, 'error', 2)),
            # Test a non-zero exit status also in extra_ok_returncodes.
            (3, False, (3, ), INFO, (None, 'done', 2)),
    ])
    def test_spinner_finish(
        self, exit_status, show_stdout, extra_ok_returncodes, log_level,
        caplog, expected,
    ):
        """
        Test that the spinner finishes correctly.
        """
        expected_exc_type = expected[0]
        expected_final_status = expected[1]
        expected_spin_count = expected[2]

        command = (
            'print("Hello"); print("world"); exit({})'.format(exit_status)
        )
        args, spinner = self.prepare_call(caplog, log_level, command=command)
        try:
            call_subprocess(
                args,
                show_stdout=show_stdout,
                extra_ok_returncodes=extra_ok_returncodes,
                spinner=spinner,
            )
        except Exception as exc:
            exc_type = type(exc)
        else:
            exc_type = None

        assert exc_type == expected_exc_type
        assert spinner.final_status == expected_final_status
        assert spinner.spin_count == expected_spin_count

    def test_closes_stdin(self):
        with pytest.raises(InstallationError):
            call_subprocess(
                [sys.executable, '-c', 'input()'],
                show_stdout=True,
            )


@pytest.mark.skipif("sys.platform == 'win32'")
def test_path_to_url_unix():
    assert path_to_url('/tmp/file') == 'file:///tmp/file'
    path = os.path.join(os.getcwd(), 'file')
    assert path_to_url('file') == 'file://' + urllib_request.pathname2url(path)


@pytest.mark.skipif("sys.platform != 'win32'")
def test_path_to_url_win():
    assert path_to_url('c:/tmp/file') == 'file:///C:/tmp/file'
    assert path_to_url('c:\\tmp\\file') == 'file:///C:/tmp/file'
    assert path_to_url(r'\\unc\as\path') == 'file://unc/as/path'
    path = os.path.join(os.getcwd(), 'file')
    assert path_to_url('file') == 'file:' + urllib_request.pathname2url(path)


@pytest.mark.parametrize('netloc, expected', [
    # Test a basic case.
    ('example.com', ('example.com', (None, None))),
    # Test with username and no password.
    ('user@example.com', ('example.com', ('user', None))),
    # Test with username and password.
    ('user:pass@example.com', ('example.com', ('user', 'pass'))),
    # Test with username and empty password.
    ('user:@example.com', ('example.com', ('user', ''))),
    # Test the password containing an @ symbol.
    ('user:pass@word@example.com', ('example.com', ('user', 'pass@word'))),
    # Test the password containing a : symbol.
    ('user:pass:word@example.com', ('example.com', ('user', 'pass:word'))),
    # Test URL-encoded reserved characters.
    ('user%3Aname:%23%40%5E@example.com',
     ('example.com', ('user:name', '#@^'))),
])
def test_split_auth_from_netloc(netloc, expected):
    actual = split_auth_from_netloc(netloc)
    assert actual == expected


@pytest.mark.parametrize('url, expected', [
    # Test a basic case.
    ('http://example.com/path#anchor',
     ('http://example.com/path#anchor', 'example.com', (None, None))),
    # Test with username and no password.
    ('http://user@example.com/path#anchor',
     ('http://example.com/path#anchor', 'example.com', ('user', None))),
    # Test with username and password.
    ('http://user:pass@example.com/path#anchor',
     ('http://example.com/path#anchor', 'example.com', ('user', 'pass'))),
    # Test with username and empty password.
    ('http://user:@example.com/path#anchor',
     ('http://example.com/path#anchor', 'example.com', ('user', ''))),
    # Test the password containing an @ symbol.
    ('http://user:pass@word@example.com/path#anchor',
     ('http://example.com/path#anchor', 'example.com', ('user', 'pass@word'))),
    # Test the password containing a : symbol.
    ('http://user:pass:word@example.com/path#anchor',
     ('http://example.com/path#anchor', 'example.com', ('user', 'pass:word'))),
    # Test URL-encoded reserved characters.
    ('http://user%3Aname:%23%40%5E@example.com/path#anchor',
     ('http://example.com/path#anchor', 'example.com', ('user:name', '#@^'))),
])
def test_split_auth_netloc_from_url(url, expected):
    actual = split_auth_netloc_from_url(url)
    assert actual == expected


@pytest.mark.parametrize('netloc, expected', [
    # Test a basic case.
    ('example.com', 'example.com'),
    # Test with username and no password.
    ('user@example.com', 'user@example.com'),
    # Test with username and password.
    ('user:pass@example.com', 'user:****@example.com'),
    # Test with username and empty password.
    ('user:@example.com', 'user:****@example.com'),
    # Test the password containing an @ symbol.
    ('user:pass@word@example.com', 'user:****@example.com'),
    # Test the password containing a : symbol.
    ('user:pass:word@example.com', 'user:****@example.com'),
    # Test URL-encoded reserved characters.
    ('user%3Aname:%23%40%5E@example.com', 'user%3Aname:****@example.com'),
])
def test_redact_netloc(netloc, expected):
    actual = redact_netloc(netloc)
    assert actual == expected


@pytest.mark.parametrize('auth_url, expected_url', [
    ('https://user:pass@domain.tld/project/tags/v0.2',
     'https://domain.tld/project/tags/v0.2'),
    ('https://domain.tld/project/tags/v0.2',
     'https://domain.tld/project/tags/v0.2',),
    ('https://user:pass@domain.tld/svn/project/trunk@8181',
     'https://domain.tld/svn/project/trunk@8181'),
    ('https://domain.tld/project/trunk@8181',
     'https://domain.tld/project/trunk@8181',),
    ('git+https://pypi.org/something',
     'git+https://pypi.org/something'),
    ('git+https://user:pass@pypi.org/something',
     'git+https://pypi.org/something'),
    ('git+ssh://git@pypi.org/something',
     'git+ssh://pypi.org/something'),
])
def test_remove_auth_from_url(auth_url, expected_url):
    url = remove_auth_from_url(auth_url)
    assert url == expected_url


@pytest.mark.parametrize('auth_url, expected_url', [
    ('https://user@example.com/abc', 'https://user@example.com/abc'),
    ('https://user:password@example.com', 'https://user:****@example.com'),
    ('https://user:@example.com', 'https://user:****@example.com'),
    ('https://example.com', 'https://example.com'),
    # Test URL-encoded reserved characters.
    ('https://user%3Aname:%23%40%5E@example.com',
     'https://user%3Aname:****@example.com'),
])
def test_redact_password_from_url(auth_url, expected_url):
    url = redact_password_from_url(auth_url)
    assert url == expected_url


@pytest.fixture()
def patch_deprecation_check_version():
    # We do this, so that the deprecation tests are easier to write.
    import pip._internal.utils.deprecation as d
    old_version = d.current_version
    d.current_version = "1.0"
    yield
    d.current_version = old_version


@pytest.mark.usefixtures("patch_deprecation_check_version")
@pytest.mark.parametrize("replacement", [None, "a magic 8 ball"])
@pytest.mark.parametrize("gone_in", [None, "2.0"])
@pytest.mark.parametrize("issue", [None, 988])
def test_deprecated_message_contains_information(gone_in, replacement, issue):
    with pytest.warns(PipDeprecationWarning) as record:
        deprecated(
            "Stop doing this!",
            replacement=replacement,
            gone_in=gone_in,
            issue=issue,
        )

    assert len(record) == 1
    message = record[0].message.args[0]

    assert "DEPRECATION: Stop doing this!" in message
    # Ensure non-None values are mentioned.
    for item in [gone_in, replacement, issue]:
        if item is not None:
            assert str(item) in message


@pytest.mark.usefixtures("patch_deprecation_check_version")
@pytest.mark.parametrize("replacement", [None, "a magic 8 ball"])
@pytest.mark.parametrize("issue", [None, 988])
def test_deprecated_raises_error_if_too_old(replacement, issue):
    with pytest.raises(PipDeprecationWarning) as exception:
        deprecated(
            "Stop doing this!",
            gone_in="1.0",  # this matches the patched version.
            replacement=replacement,
            issue=issue,
        )

    message = exception.value.args[0]

    assert "DEPRECATION: Stop doing this!" in message
    assert "1.0" in message
    # Ensure non-None values are mentioned.
    for item in [replacement, issue]:
        if item is not None:
            assert str(item) in message


@pytest.mark.usefixtures("patch_deprecation_check_version")
def test_deprecated_message_reads_well():
    with pytest.raises(PipDeprecationWarning) as exception:
        deprecated(
            "Stop doing this!",
            gone_in="1.0",  # this matches the patched version.
            replacement="to be nicer",
            issue="100000",  # I hope we never reach this number.
        )

    message = exception.value.args[0]

    assert message == (
        "DEPRECATION: Stop doing this! "
        "pip 1.0 will remove support for this functionality. "
        "A possible replacement is to be nicer. "
        "You can find discussion regarding this at "
        "https://github.com/pypa/pip/issues/100000."
    )


@pytest.mark.parametrize("unbuffered_output", [False, True])
def test_make_setuptools_shim_args(unbuffered_output):
    args = make_setuptools_shim_args(
        "/dir/path/setup.py",
        unbuffered_output=unbuffered_output
    )

    assert ("-u" in args) == unbuffered_output

    assert args[-2] == "-c"

    assert "sys.argv[0] = '/dir/path/setup.py'" in args[-1]
    assert "__file__='/dir/path/setup.py'" in args[-1]
