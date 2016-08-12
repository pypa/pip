import os
import textwrap
import pytest

from tests.lib.path import Path


def fake_wheel(data, wheel_path):
    data.packages.join(
        'simple.dist-0.1-py2.py3-none-any.whl'
    ).copy(data.packages.join(wheel_path))


@pytest.mark.network
def test_download_if_requested(script):
    """
    It should download (in the scratch path) and not install if requested.
    """
    result = script.pip(
        'download', '-d', 'pip_downloads', 'INITools==0.1', expect_error=True
    )
    assert Path('scratch') / 'pip_downloads' / 'INITools-0.1.tar.gz' \
        in result.files_created
    assert script.site_packages / 'initools' not in result.files_created


@pytest.mark.network
def test_download_setuptools(script):
    """
    It should download (in the scratch path) and not install if requested.
    """
    result = script.pip('download', 'setuptools')
    setuptools_prefix = str(Path('scratch') / 'setuptools')
    assert any(
        path.startswith(setuptools_prefix) for path in result.files_created
    )


def test_download_wheel(script, data):
    """
    Test using "pip download" to download a *.whl archive.
    """
    result = script.pip(
        'download',
        '--no-index',
        '-f', data.packages,
        '-d', '.', 'meta'
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
        'download', '-r', script.scratch_path / 'test-req.txt', '-d', '.',
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
        'download', 'Paste[openid]==1.7.5.1', '-d', '.', expect_error=True,
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
        'download', wheel_path,
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
        'download', wheel_path,
        '-d', '.', '--find-links', data.find_links, '--no-index'
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
        'download', '-r', script.scratch_path / 'test-req.txt', '-d', '.',
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
        'download', '-r', script.scratch_path / 'test-req.txt', '-d', '.',
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
        'download', '-d', '.', 'git+git://github.com/pypa/pip-test-package.git'
    )
    assert (
        Path('scratch') / 'pip-test-package-0.1.1.zip'
        in result.files_created
    )
    assert script.site_packages / 'piptestpackage' not in result.files_created


def test_download_specify_platform_only_binary(script, data):
    """
    Confirm that specifying an interpreter/platform constraint
    enforces that ``--only-binary=:all:`` is set.
    """
    fake_wheel(data, 'fake-1.0-py2.py3-none-any.whl')

    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--platform', 'linux_x86_64',
        'fake'
    )
    assert (
        Path('scratch') / 'fake-1.0-py2.py3-none-any.whl'
        in result.files_created
    )

    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--dest', '.',
        '--platform', 'linux_x86_64',
        'fake',
        expect_error=True,
    )
    assert '--only-binary=:all:' in result.stderr

    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--dest', '.',
        '--platform', 'linux_x86_64',
        'fake',
        expect_error=True,
    )
    assert '--only-binary=:all:' in result.stderr

    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--no-binary=fake',
        '--dest', '.',
        '--platform', 'linux_x86_64',
        'fake',
        expect_error=True,
    )
    assert '--only-binary=:all:' in result.stderr


def test_download_specify_platform(script, data):
    """
    Test using "pip download --platform" to download a .whl archive
    supported for a specific platform
    """
    fake_wheel(data, 'fake-1.0-py2.py3-none-any.whl')

    # Confirm that universal wheels are returned even for specific
    # platforms.
    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--platform', 'linux_x86_64',
        'fake'
    )
    assert (
        Path('scratch') / 'fake-1.0-py2.py3-none-any.whl'
        in result.files_created
    )

    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--platform', 'macosx_10_9_x86_64',
        'fake'
    )

    data.reset()
    fake_wheel(data, 'fake-1.0-py2.py3-none-macosx_10_9_x86_64.whl')
    fake_wheel(data, 'fake-2.0-py2.py3-none-linux_x86_64.whl')

    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--platform', 'macosx_10_10_x86_64',
        'fake'
    )
    assert (
        Path('scratch') /
        'fake-1.0-py2.py3-none-macosx_10_9_x86_64.whl'
        in result.files_created
    )

    # OSX platform wheels are not backward-compatible.
    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--platform', 'macosx_10_8_x86_64',
        'fake',
        expect_error=True,
    )

    # No linux wheel provided for this version.
    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--platform', 'linux_x86_64',
        'fake==1',
        expect_error=True,
    )

    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--platform', 'linux_x86_64',
        'fake==2'
    )
    assert (
        Path('scratch') / 'fake-2.0-py2.py3-none-linux_x86_64.whl'
        in result.files_created
    )


def test_download_platform_manylinux(script, data):
    """
    Test using "pip download --platform" to download a .whl archive
    supported for a specific platform.
    """
    fake_wheel(data, 'fake-1.0-py2.py3-none-any.whl')
    # Confirm that universal wheels are returned even for specific
    # platforms.
    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--platform', 'linux_x86_64',
        'fake',
    )
    assert (
        Path('scratch') / 'fake-1.0-py2.py3-none-any.whl'
        in result.files_created
    )

    data.reset()
    fake_wheel(data, 'fake-1.0-py2.py3-none-manylinux1_x86_64.whl')
    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--platform', 'manylinux1_x86_64',
        'fake',
    )
    assert (
        Path('scratch') /
        'fake-1.0-py2.py3-none-manylinux1_x86_64.whl'
        in result.files_created
    )

    # When specifying the platform, manylinux1 needs to be the
    # explicit platform--it won't ever be added to the compatible
    # tags.
    data.reset()
    fake_wheel(data, 'fake-1.0-py2.py3-none-linux_x86_64.whl')
    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--platform', 'linux_x86_64',
        'fake',
        expect_error=True,
    )


def test_download_specify_python_version(script, data):
    """
    Test using "pip download --python-version" to download a .whl archive
    supported for a specific interpreter
    """
    fake_wheel(data, 'fake-1.0-py2.py3-none-any.whl')
    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--python-version', '2',
        'fake'
    )
    assert (
        Path('scratch') / 'fake-1.0-py2.py3-none-any.whl'
        in result.files_created
    )

    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--python-version', '3',
        'fake'
    )

    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--python-version', '27',
        'fake'
    )

    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--python-version', '33',
        'fake'
    )

    data.reset()
    fake_wheel(data, 'fake-1.0-py2-none-any.whl')
    fake_wheel(data, 'fake-2.0-py3-none-any.whl')

    # No py3 provided for version 1.
    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--python-version', '3',
        'fake==1.0',
        expect_error=True,
    )

    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--python-version', '2',
        'fake'
    )
    assert (
        Path('scratch') / 'fake-1.0-py2-none-any.whl'
        in result.files_created
    )

    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--python-version', '26',
        'fake'
    )

    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--python-version', '3',
        'fake'
    )
    assert (
        Path('scratch') / 'fake-2.0-py3-none-any.whl'
        in result.files_created
    )


def test_download_specify_abi(script, data):
    """
    Test using "pip download --abi" to download a .whl archive
    supported for a specific abi
    """
    fake_wheel(data, 'fake-1.0-py2.py3-none-any.whl')
    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--implementation', 'fk',
        '--abi', 'fake_abi',
        'fake'
    )
    assert (
        Path('scratch') / 'fake-1.0-py2.py3-none-any.whl'
        in result.files_created
    )

    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--implementation', 'fk',
        '--abi', 'none',
        'fake'
    )

    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--abi', 'cp27m',
        'fake',
        expect_error=True,
    )

    data.reset()
    fake_wheel(data, 'fake-1.0-fk2-fakeabi-fake_platform.whl')
    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--python-version', '2',
        '--implementation', 'fk',
        '--platform', 'fake_platform',
        '--abi', 'fakeabi',
        'fake'
    )
    assert (
        Path('scratch') / 'fake-1.0-fk2-fakeabi-fake_platform.whl'
        in result.files_created
    )

    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--implementation', 'fk',
        '--platform', 'fake_platform',
        '--abi', 'none',
        'fake',
        expect_error=True,
    )


def test_download_specify_implementation(script, data):
    """
    Test using "pip download --abi" to download a .whl archive
    supported for a specific abi
    """
    fake_wheel(data, 'fake-1.0-py2.py3-none-any.whl')
    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--implementation', 'fk',
        'fake'
    )
    assert (
        Path('scratch') / 'fake-1.0-py2.py3-none-any.whl'
        in result.files_created
    )

    data.reset()
    fake_wheel(data, 'fake-1.0-fk2.fk3-none-any.whl')
    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--implementation', 'fk',
        'fake'
    )
    assert (
        Path('scratch') / 'fake-1.0-fk2.fk3-none-any.whl'
        in result.files_created
    )

    data.reset()
    fake_wheel(data, 'fake-1.0-fk3-none-any.whl')
    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--implementation', 'fk',
        '--python-version', '3',
        'fake'
    )
    assert (
        Path('scratch') / 'fake-1.0-fk3-none-any.whl'
        in result.files_created
    )

    result = script.pip(
        'download', '--no-index', '--find-links', data.find_links,
        '--only-binary=:all:',
        '--dest', '.',
        '--implementation', 'fk',
        '--python-version', '2',
        'fake',
        expect_error=True,
    )
