import os

from pip.backwardcompat import ConfigParser
from pip.download import path_to_url2
from tests.test_pip import here, reset_env, run_pip, pyversion

from tests.path import Path


def test_index():
    """
    Test that the pip.ini is written and works from an index (PyPI).
    """
    env = reset_env()
    run_pip('install', '-i http://pypi.python.org/simple/', 'INITools==0.3.1')

    egg_info_dir = env.base_path / env.site_packages / 'INITools-0.3.1-py%s.egg-info' % pyversion

    infofp = open(os.path.join(egg_info_dir, "pip.ini"))
    info = ConfigParser.RawConfigParser()
    info.readfp(infofp)
    infofp.close()

    assert info.has_section("download")
    assert info.get("download", "url").startswith("http://pypi.python.org/packages/source/I/INITools/INITools")
    assert info.get("download", "requirement") == "INITools==0.3.1"


def test_tarball():
    """
    Test that the pip.ini is written and works from an tarball.
    """
    env = reset_env()
    run_pip('install', 'http://pypi.python.org/packages/source/I/INITools/INITools-0.3.1.tar.gz')

    egg_info_dir = env.base_path / env.site_packages / 'INITools-0.3.1-py%s.egg-info' % pyversion

    infofp = open(os.path.join(egg_info_dir, "pip.ini"))
    info = ConfigParser.RawConfigParser()
    info.readfp(infofp)
    infofp.close()

    assert info.has_section("download")
    assert info.get("download", "url") == "http://pypi.python.org/packages/source/I/INITools/INITools-0.3.1.tar.gz"
    assert info.get("download", "requirement") == "http://pypi.python.org/packages/source/I/INITools/INITools-0.3.1.tar.gz"


def test_editable():
    """
    Test that the pip.ini is written and works from an editable.
    """
    env = reset_env()
    fspkg = path_to_url2(Path(here) / 'packages' / 'FSPkg')
    run_pip('install', '-e', fspkg)

    egg_info_dir = Path(here) / 'packages' / 'FSPkg' / 'FSPkg.egg-info'

    infofp = open(os.path.join(egg_info_dir, "pip.ini"))
    info = ConfigParser.RawConfigParser()
    info.readfp(infofp)
    infofp.close()

    assert info.has_section("download")
    assert info.get("download", "url") == fspkg
    assert info.get("download", "requirement") == "--editable=" + fspkg
