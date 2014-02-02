import os
import textwrap

from tests.lib.path import Path


def test_download_if_requested(script):
    """
    It should download (in the scratch path) and not install if requested.
    """
    result = script.pip(
        'install', 'INITools==0.1', '-d', '.', expect_error=True
    )
    assert Path('scratch') / 'INITools-0.1.tar.gz' in result.files_created
    assert script.site_packages / 'initools' not in result.files_created


def test_download_wheel(script):
    """
    Test using "pip install --download" to download a *.whl archive.
    FIXME: this test could use a local --find-links dir, but -d with local
           --find-links has a bug https://github.com/pypa/pip/issues/1111
    """
    result = script.pip(
        'install', '--use-wheel',
        '-f', 'https://bitbucket.org/pypa/pip-test-package/downloads',
        '-d', '.', 'pip-test-package'
    )
    assert (
        Path('scratch') / 'pip_test_package-0.1.1-py2.py3-none-any.whl'
        in result.files_created
    )
    assert script.site_packages / 'piptestpackage' not in result.files_created


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
        '-d', '.', '--no-deps'
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
        '-d', '.', '--find-links', data.find_links, '--no-index'
    )
    assert Path('scratch') / wheel_filename in result.files_created
    assert Path('scratch') / dep_filename in result.files_created


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
