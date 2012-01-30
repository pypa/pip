from pip.backwardcompat import urllib

from pip.req import InstallRequirement
from pip.index import PackageFinder

from tests.path import Path
from tests.test_pip import here

find_links = 'file://' + urllib.quote(str(Path(here).abspath/'packages').replace('\\', '/'))


def test_no_mpkg():
    """Finder skips zipfiles with "macosx10" in the name."""
    finder = PackageFinder([find_links], [])
    req = InstallRequirement.from_line("pkgwithmpkg")
    found = finder.find_requirement(req, False)

    assert found.url.endswith("pkgwithmpkg-1.0.tar.gz"), found
