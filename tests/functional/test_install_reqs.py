import os.path
import textwrap

import pytest

from tests.lib import (pyversion, path_to_url,
                       _create_test_package_with_subdirectory)
from tests.lib.local_repos import local_checkout


def test_requirements_file(script):
    """
    Test installing from a requirements file.

    """
    other_lib_name, other_lib_version = 'anyjson', '0.3'
    script.scratch_path.join("initools-req.txt").write(textwrap.dedent("""\
        INITools==0.2
        # and something else to test out:
        %s<=%s
        """ % (other_lib_name, other_lib_version)))
    result = script.pip(
        'install', '-r', script.scratch_path / 'initools-req.txt'
    )
    assert (
        script.site_packages / 'INITools-0.2-py%s.egg-info' %
        pyversion in result.files_created
    )
    assert script.site_packages / 'initools' in result.files_created
    assert result.files_created[script.site_packages / other_lib_name].dir
    fn = '%s-%s-py%s.egg-info' % (other_lib_name, other_lib_version, pyversion)
    assert result.files_created[script.site_packages / fn].dir


def test_schema_check_in_requirements_file(script):
    """
    Test installing from a requirements file with an invalid vcs schema..

    """
    script.scratch_path.join("file-egg-req.txt").write(
        "\n%s\n" % (
            "git://github.com/alex/django-fixture-generator.git"
            "#egg=fixture_generator"
        )
    )

    with pytest.raises(AssertionError):
        script.pip(
            "install", "-vvv", "-r", script.scratch_path / "file-egg-req.txt"
        )


def test_relative_requirements_file(script, data):
    """
    Test installing from a requirements file with a relative path with an
    egg= definition..

    """
    url = path_to_url(
        os.path.join(data.root, "packages", "..", "packages", "FSPkg")
    ) + '#egg=FSPkg'
    script.scratch_path.join("file-egg-req.txt").write(textwrap.dedent("""\
        %s
        """ % url))
    result = script.pip(
        'install', '-vvv', '-r', script.scratch_path / 'file-egg-req.txt'
    )
    assert (
        script.site_packages / 'FSPkg-0.1dev-py%s.egg-info' % pyversion
    ) in result.files_created, str(result)
    assert (script.site_packages / 'fspkg') in result.files_created, (
        str(result.stdout)
    )


def test_multiple_requirements_files(script, tmpdir):
    """
    Test installing from multiple nested requirements files.

    """
    other_lib_name, other_lib_version = 'anyjson', '0.3'
    script.scratch_path.join("initools-req.txt").write(
        textwrap.dedent("""
            -e %s@10#egg=INITools-dev
            -r %s-req.txt
        """) %
        (
            local_checkout(
                'svn+http://svn.colorstudy.com/INITools/trunk',
                tmpdir.join("cache"),
            ),
            other_lib_name
        ),
    )
    script.scratch_path.join("%s-req.txt" % other_lib_name).write(
        "%s<=%s" % (other_lib_name, other_lib_version)
    )
    result = script.pip(
        'install', '-r', script.scratch_path / 'initools-req.txt'
    )
    assert result.files_created[script.site_packages / other_lib_name].dir
    fn = '%s-%s-py%s.egg-info' % (other_lib_name, other_lib_version, pyversion)
    assert result.files_created[script.site_packages / fn].dir
    assert script.venv / 'src' / 'initools' in result.files_created


def test_respect_order_in_requirements_file(script, data):
    script.scratch_path.join("frameworks-req.txt").write(textwrap.dedent("""\
        parent
        child
        simple
        """))

    result = script.pip(
        'install', '--no-index', '-f', data.find_links, '-r',
        script.scratch_path / 'frameworks-req.txt'
    )

    downloaded = [line for line in result.stdout.split('\n')
                  if 'Downloading/unpacking' in line]

    assert 'parent' in downloaded[0], (
        'First download should be "parent" but was "%s"' % downloaded[0]
    )
    assert 'child' in downloaded[1], (
        'Second download should be "child" but was "%s"' % downloaded[1]
    )
    assert 'simple' in downloaded[2], (
        'Third download should be "simple" but was "%s"' % downloaded[2]
    )


def test_install_local_editable_with_subdirectory(script):
    version_pkg_path = _create_test_package_with_subdirectory(script,
                                                              'version_subdir')
    result = script.pip(
        'install', '-e',
        '%s#egg=version_subpkg&subdirectory=version_subdir' %
        ('git+file://%s' % version_pkg_path,)
    )

    result.assert_installed('version-subpkg', sub_dir='version_subdir')
