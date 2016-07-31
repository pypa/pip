import os
import textwrap
import pytest

from tests.lib.path import Path


@pytest.mark.network
def test_download_if_requested(script):
    """
    It should download (in the scratch path) and not install if requested.
    """
    result = script.pip(
        'install', 'INITools==0.1', '-d', '.', expect_error=True
    )
    assert Path('scratch') / 'INITools-0.1.tar.gz' in result.files_created
    assert script.site_packages / 'initools' not in result.files_created


def test_download_wheel(script, data):
    """
    Test using "pip install --download" to download a *.whl archive.
    """
    result = script.pip(
        'install',
        '--no-index',
        '-f', data.packages,
        '-d', '.', 'meta',
        expect_stderr=True,
    )
    assert (
        Path('scratch') / 'meta-1.0-py2.py3-none-any.whl'
        in result.files_created
    )
    assert script.site_packages / 'piptestpackage' not in result.files_created


@pytest.mark.network
def test_single_download_from_requirements_file(script):
    """
    It should support download (in the scratch path) from PyPi from a
    requirements file
    """
    script.scratch_path.join("test-req.txt").write(textwrap.dedent("""
        INITools==0.1
        """))
    result = script.pip(
        'install', '-r', script.scratch_path / 'test-req.txt', '-d', '.',
        expect_error=True,
    )
    assert Path('scratch') / 'INITools-0.1.tar.gz' in result.files_created
    assert script.site_packages / 'initools' not in result.files_created


@pytest.mark.network
def test_download_should_download_dependencies(script):
    """
    It should download dependencies (in the scratch path)
    """
    result = script.pip(
        'install', 'Paste[openid]==1.7.5.1', '-d', '.', expect_error=True,
    )
    assert Path('scratch') / 'Paste-1.7.5.1.tar.gz' in result.files_created
    openid_tarball_prefix = str(Path('scratch') / 'python-openid-')
    assert any(
        path.startswith(openid_tarball_prefix) for path in result.files_created
    )
    assert script.site_packages / 'openid' not in result.files_created


def test_download_wheel_archive(script, data):
    """
    It should download a wheel archive path
    """
    wheel_filename = 'colander-0.9.9-py2.py3-none-any.whl'
    wheel_path = os.path.join(data.find_links, wheel_filename)
    result = script.pip(
        'install', wheel_path,
        '-d', '.', '--no-deps',
        expect_stderr=True,
    )
    assert Path('scratch') / wheel_filename in result.files_created


def test_download_should_download_wheel_deps(script, data):
    """
    It should download dependencies for wheels(in the scratch path)
    """
    wheel_filename = 'colander-0.9.9-py2.py3-none-any.whl'
    dep_filename = 'translationstring-1.1.tar.gz'
    wheel_path = os.path.join(data.find_links, wheel_filename)
    result = script.pip(
        'install', wheel_path,
        '-d', '.', '--find-links', data.find_links, '--no-index',
        expect_stderr=True,
    )
    assert Path('scratch') / wheel_filename in result.files_created
    assert Path('scratch') / dep_filename in result.files_created


@pytest.mark.network
def test_download_should_skip_existing_files(script):
    """
    It should not download files already existing in the scratch dir
    """
    script.scratch_path.join("test-req.txt").write(textwrap.dedent("""
        INITools==0.1
        """))

    result = script.pip(
        'install', '-r', script.scratch_path / 'test-req.txt', '-d', '.',
        expect_error=True,
    )
    assert Path('scratch') / 'INITools-0.1.tar.gz' in result.files_created
    assert script.site_packages / 'initools' not in result.files_created

    # adding second package to test-req.txt
    script.scratch_path.join("test-req.txt").write(textwrap.dedent("""
        INITools==0.1
        python-openid==2.2.5
        """))

    # only the second package should be downloaded
    result = script.pip(
        'install', '-r', script.scratch_path / 'test-req.txt', '-d', '.',
        expect_error=True,
    )
    openid_tarball_prefix = str(Path('scratch') / 'python-openid-')
    assert any(
        path.startswith(openid_tarball_prefix) for path in result.files_created
    )
    assert Path('scratch') / 'INITools-0.1.tar.gz' not in result.files_created
    assert script.site_packages / 'initools' not in result.files_created
    assert script.site_packages / 'openid' not in result.files_created


@pytest.mark.network
def test_download_vcs_link(script):
    """
    It should allow -d flag for vcs links, regression test for issue #798.
    """
    result = script.pip(
        'install', '-d', '.', 'git+git://github.com/pypa/pip-test-package.git',
        expect_stderr=True,
    )
    assert (
        Path('scratch') / 'pip-test-package-0.1.1.zip'
        in result.files_created
    )
    assert script.site_packages / 'piptestpackage' not in result.files_created
