# -*- coding: utf-8 -*-

"""
util tests

"""
import os
import shutil
import stat
import sys
import tempfile
import time
import warnings

import pytest
from mock import Mock, patch
from pip._vendor.six import BytesIO

from pip._internal.exceptions import (
    HashMismatch, HashMissing, InstallationError, UnsupportedPythonVersion,
)
from pip._internal.utils.encoding import auto_decode
from pip._internal.utils.glibc import check_glibc_version
from pip._internal.utils.hashes import Hashes, MissingHashes
from pip._internal.utils.misc import (
    call_subprocess, egg_link_path, ensure_dir, get_installed_distributions,
    get_prog, normalize_path, remove_auth_from_url, rmtree, untar_file,
    unzip_file,
)
from pip._internal.utils.packaging import check_dist_requires_python
from pip._internal.utils.temp_dir import TempDirectory


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
        for fname, expected_mode, test in [
                ('file.txt', 0o644, os.path.isfile),
                ('symlink.txt', 0o644, os.path.isfile),
                ('script_owner.sh', 0o755, os.path.isfile),
                ('script_group.sh', 0o755, os.path.isfile),
                ('script_world.sh', 0o755, os.path.isfile),
                ('dir', 0o755, os.path.isdir),
                (os.path.join('dir', 'dirfile'), 0o644, os.path.isfile)]:
            path = os.path.join(self.tempdir, fname)
            if path.endswith('symlink.txt') and sys.platform == 'win32':
                # no symlinks created on windows
                continue
            assert test(path), path
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
        test_file = data.packages.join("test_tar.tgz")
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
        test_file = data.packages.join("test_zip.zip")
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

    def test_success(self, tmpdir):
        """Make sure no error is raised when at least one hash matches.

        Test check_against_path because it calls everything else.

        """
        file = tmpdir / 'to_hash'
        file.write('hello')
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

    def test_auto_decode_utf16_le(self):
        data = (
            b'\xff\xfeD\x00j\x00a\x00n\x00g\x00o\x00=\x00'
            b'=\x001\x00.\x004\x00.\x002\x00'
        )
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


class TestGlibc(object):
    def test_manylinux1_check_glibc_version(self):
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


class TestCheckRequiresPython(object):

    @pytest.mark.parametrize(
        ("metadata", "should_raise"),
        [
            ("Name: test\n", False),
            ("Name: test\nRequires-Python:", False),
            ("Name: test\nRequires-Python: invalid_spec", False),
            ("Name: test\nRequires-Python: <=1", True),
        ],
    )
    def test_check_requires(self, metadata, should_raise):
        fake_dist = Mock(
            has_metadata=lambda _: True,
            get_metadata=lambda _: metadata)
        if should_raise:
            with pytest.raises(UnsupportedPythonVersion):
                check_dist_requires_python(fake_dist)
        else:
            check_dist_requires_python(fake_dist)


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


def test_call_subprocess_works_okay_when_just_given_nothing():
    try:
        call_subprocess([sys.executable, '-c', 'print("Hello")'])
    except Exception:
        assert False, "Expected subprocess call to succeed"


def test_call_subprocess_closes_stdin():
    with pytest.raises(InstallationError):
        call_subprocess([sys.executable, '-c', 'input()'])


def test_remove_auth_from_url():
    # Check that the url is doctored appropriately to remove auth elements
    #    from the url
    svn_auth_url = 'https://user:pass@svnrepo.org/svn/project/tags/v0.2'
    expected_url = 'https://svnrepo.org/svn/project/tags/v0.2'
    url = remove_auth_from_url(svn_auth_url)
    assert url == expected_url

    # Check that this doesn't impact urls without authentication'
    svn_noauth_url = 'https://svnrepo.org/svn/project/tags/v0.2'
    expected_url = svn_noauth_url
    url = remove_auth_from_url(svn_noauth_url)
    assert url == expected_url

    # Check that links to specific revisions are handled properly
    svn_rev_url = 'https://user:pass@svnrepo.org/svn/project/trunk@8181'
    expected_url = 'https://svnrepo.org/svn/project/trunk@8181'
    url = remove_auth_from_url(svn_rev_url)
    assert url == expected_url

    svn_rev_url = 'https://svnrepo.org/svn/project/trunk@8181'
    expected_url = 'https://svnrepo.org/svn/project/trunk@8181'
    url = remove_auth_from_url(svn_rev_url)
    assert url == expected_url
