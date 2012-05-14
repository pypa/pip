from pip.req import InstallRequirement


def test_url_with_query():
    """InstallRequirement should strip the fragment, but not the query."""
    url = 'http://foo.com/?p=bar.git;a=snapshot;h=v0.1;sf=tgz'
    fragment = '#egg=bar'
    req = InstallRequirement.from_line(url + fragment)

    assert req.url == url, req.url
