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
    assert (env.site_packages/'fspkg') in result.files_created, str(result.stdout)
    assert (env.site_packages/'FSPkg-0.1dev-py%s.egg-info' % pyversion) in result.files_created, str(result)
