import os
import pytest
from tests.lib.path import Path


def test_install_from_wheel(script, data):
    """
    Test installing from a wheel (that has a script)
    """
    result = script.pip('install', 'has.script==1.0', '--use-wheel',
                     '--no-index', '--find-links='+data.find_links,
                     expect_error=False)
    dist_info_folder = script.site_packages/'has.script-1.0.dist-info'
    assert dist_info_folder in result.files_created, (dist_info_folder,
                                                      result.files_created,
                                                      result.stdout)
    script_file = script.bin / 'script.py'
    assert script_file in result.files_created


def test_install_from_wheel_with_extras(script, data):
    """
    Test installing from a wheel with extras.
    """
    result = script.pip('install', 'complex-dist[simple]', '--use-wheel',
                     '--no-index', '--find-links='+data.find_links,
                     expect_error=False)
    dist_info_folder = script.site_packages/'complex_dist-0.1.dist-info'
    assert dist_info_folder in result.files_created, (dist_info_folder,
                                                      result.files_created,
                                                      result.stdout)
    dist_info_folder = script.site_packages/'simple.dist-0.1.dist-info'
    assert dist_info_folder in result.files_created, (dist_info_folder,
                                                      result.files_created,
                                                      result.stdout)


def test_install_from_wheel_file(script, data):
    """
    Test installing directly from a wheel file.
    """
    package = data.packages.join("headers.dist-0.1-py2.py3-none-any.whl")
    result = script.pip('install', package, '--no-index', expect_error=False)
    dist_info_folder = script.site_packages/'headers.dist-0.1.dist-info'
    assert dist_info_folder in result.files_created, (dist_info_folder,
                                                      result.files_created,
                                                      result.stdout)


def test_install_wheel_with_target(script, data):
    """
    Test installing a wheel using pip install --target
    """
    script.pip_install_local('wheel')
    target_dir = script.scratch_path/'target'
    result = script.pip('install', 'simple.dist==0.1', '-t', target_dir, '--use-wheel',
                     '--no-index', '--find-links='+data.find_links)
    assert Path('scratch')/'target'/'simpledist' in result.files_created, str(result)


def test_install_wheel_with_root(script, data):
    """
    Test installing a wheel using pip install --root
    """
    root_dir = script.scratch_path/'root'
    result = script.pip('install', 'simple.dist==0.1', '--root', root_dir, '--use-wheel',
                     '--no-index', '--find-links='+data.find_links)
    assert Path('scratch')/'root' in result.files_created


def test_install_from_wheel_installs_deps(script, data):
    """
    Test can install dependencies of wheels
    """
    # 'requires_source' depends on the 'source' project
    package = data.packages.join("requires_source-1.0-py2.py3-none-any.whl")
    result = script.pip('install', '--no-index', '--find-links', data.find_links, package)
    result.assert_installed('source', editable=False)


def test_install_from_wheel_no_deps(script, data):
    """
    Test --no-deps works with wheel installs
    """
    # 'requires_source' depends on the 'source' project
    package = data.packages.join("requires_source-1.0-py2.py3-none-any.whl")
    result = script.pip('install', '--no-index', '--find-links', data.find_links, '--no-deps', package)
    pkg_folder = script.site_packages/'source'
    assert pkg_folder not in result.files_created


# --user option is broken in pypy
@pytest.mark.skipif("hasattr(sys, 'pypy_version_info')")
def test_install_user_wheel(script, virtualenv, data):
    """
    Test user install from wheel (that has a script)
    """
    virtualenv.system_site_packages = True
    script.pip_install_local('wheel')
    result = script.pip('install', 'has.script==1.0', '--user', '--use-wheel',
                 '--no-index', '--find-links='+data.find_links)
    egg_info_folder = script.user_site / 'has.script-1.0.dist-info'
    assert egg_info_folder in result.files_created, str(result)
    script_file = script.user_bin / 'script.py'
    assert script_file in result.files_created

def test_install_from_wheel_gen_entrypoint(script, data):
    """
    Test installing scripts (entry points are generated)
    """
    result = script.pip('install', 'script.wheel1a==0.1', '--use-wheel',
                     '--no-index', '--find-links='+data.find_links,
                     expect_error=False)
    if os.name == 'nt':
        wrapper_file = script.bin / 't1.exe'
    else:
        wrapper_file = script.bin / 't1'
    assert wrapper_file in result.files_created

def test_install_from_wheel_with_legacy(script, data):
    """
    Test installing scripts (legacy scripts are preserved)
    """
    result = script.pip('install', 'script.wheel2a==0.1', '--use-wheel',
                     '--no-index', '--find-links='+data.find_links,
                     expect_error=False)

    legacy_file1 = script.bin / 'testscript1.bat'
    legacy_file2 = script.bin / 'testscript2'

    assert legacy_file1 in result.files_created
    assert legacy_file2 in result.files_created

def test_install_from_wheel_no_setuptools_entrypoint(script, data):
    """
    Test installing scripts (setuptools entrypoints are omitted)
    """
    result = script.pip('install', 'script.wheel1==0.1', '--use-wheel',
                     '--no-index', '--find-links='+data.find_links,
                     expect_error=False)
    if os.name == 'nt':
        wrapper_file = script.bin / 't1.exe'
    else:
        wrapper_file = script.bin / 't1'
    wrapper_helper = script.bin / 't1-script.py'

    assert wrapper_file in result.files_created
    assert wrapper_helper not in result.files_created


def test_skipping_setuptools_doesnt_skip_legacy(script, data):
    """
    Test installing scripts (legacy scripts are preserved even when we skip setuptools wrappers)
    """
    result = script.pip('install', 'script.wheel2==0.1', '--use-wheel',
                     '--no-index', '--find-links='+data.find_links,
                     expect_error=False)

    legacy_file1 = script.bin / 'testscript1.bat'
    legacy_file2 = script.bin / 'testscript2'
    wrapper_helper = script.bin / 't1-script.py'

    assert legacy_file1 in result.files_created
    assert legacy_file2 in result.files_created
    assert wrapper_helper not in result.files_created

def test_install_from_wheel_gui_entrypoint(script, data):
    """
    Test installing scripts (gui entry points are generated)
    """
    result = script.pip('install', 'script.wheel3==0.1', '--use-wheel',
                     '--no-index', '--find-links='+data.find_links,
                     expect_error=False)
    if os.name == 'nt':
        wrapper_file = script.bin / 't1.exe'
    else:
        wrapper_file = script.bin / 't1'
    assert wrapper_file in result.files_created

