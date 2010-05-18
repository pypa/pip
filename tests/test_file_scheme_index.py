from test_pip import here, reset_env, run_pip, pyversion
from path import Path
from urllib import pathname2url

index_url = 'file://' + pathname2url(Path(here).abspath/'index')

def test_install():
    """
    Test installing from a local index.

    """
    env = reset_env()
    result = run_pip('install', '-vvv', '--index-url', index_url, 'FSPkg', expect_error=False)
    site_packages = Path('site-packages')
    assert [ x for x in result.files_created if x.endswith(site_packages/'fspkg') ], str(result)
    assert [ x for x in result.files_created if x.endswith(site_packages/'FSPkg-0.1dev-py%s.egg-info' % pyversion) ], str(result)
