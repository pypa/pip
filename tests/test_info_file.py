import os

from pip.backwardcompat import ConfigParser
from pip.download import path_to_url2
from tests.test_pip import here, reset_env, run_pip
from tests.path import Path


def test_index():
    """
    Test that the info.ini is written and works from an index (PyPI).
    """
    env = reset_env()
    run_pip('install', '-i http://pypi.python.org/simple/', 'INITools')

    egg_info_dir = None
    for x in os.listdir(os.path.join(os.path.dirname(env.venv_path), env.site_packages)):
        if x.startswith("INITools-") and x.endswith(".egg-info"):
            egg_info_dir = os.path.join(os.path.dirname(env.venv_path), env.site_packages, x)
            break
    assert egg_info_dir is not None

    infofp = open(os.path.join(os.path.dirname(env.venv_path), env.site_packages, egg_info_dir, "info.ini"))
    info = ConfigParser.RawConfigParser()
    info.readfp(infofp)
    infofp.close()

    assert info.has_section("download")
    assert info.get("download", "url").startswith("http://pypi.python.org/packages/source/I/INITools/INITools")
    assert info.get("download", "requirement") == "INITools"


def test_tarball():
    """
    Test that the info.ini is written and works from an tarball.
    """
    env = reset_env()
    run_pip('install', 'http://pypi.python.org/packages/source/I/INITools/INITools-0.3.1.tar.gz')

    egg_info_dir = None
    for x in os.listdir(os.path.join(os.path.dirname(env.venv_path), env.site_packages)):
        if x.startswith("INITools-") and x.endswith(".egg-info"):
            egg_info_dir = os.path.join(os.path.dirname(env.venv_path), env.site_packages, x)
            break
    assert egg_info_dir is not None

    infofp = open(os.path.join(egg_info_dir, "info.ini"))
    info = ConfigParser.RawConfigParser()
    info.readfp(infofp)
    infofp.close()

    assert info.has_section("download")
    assert info.get("download", "url") == "http://pypi.python.org/packages/source/I/INITools/INITools-0.3.1.tar.gz"
    assert info.get("download", "requirement") == "http://pypi.python.org/packages/source/I/INITools/INITools-0.3.1.tar.gz"


def test_editable():
    """
    Test that the info.ini is written and works from an editable.
    """
    env = reset_env()
    fspkg = path_to_url2(Path(here) / 'packages' / 'FSPkg')
    run_pip('install', '-e', fspkg)

    egg_info_dir = None
    for x in os.listdir(Path(here) / 'packages' / 'FSPkg'):
        if x.startswith("FSPkg") and x.endswith(".egg-info"):
            egg_info_dir = os.path.join(Path(here) / 'packages' / 'FSPkg', x)
            break
    assert egg_info_dir is not None

    infofp = open(os.path.join(egg_info_dir, "info.ini"))
    info = ConfigParser.RawConfigParser()
    info.readfp(infofp)
    infofp.close()

    assert info.has_section("download")
    assert info.get("download", "url") == "file:///Users/dstufft/projects/pip/tests/packages/FSPkg"
    assert info.get("download", "requirement") == "--editable=file:///Users/dstufft/projects/pip/tests/packages/FSPkg"
