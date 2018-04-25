from pip._internal.vcs.helix_core import join_url, split_url

url1 = "p4+p4:///foo/bar"
url2 = "p4+ssl://myname:p4ssw0rd@myserver:1234/baz/zyz@456"
parts1 = ('tcp:perforce:1666', '/foo/bar', None, '', '')
parts2 = ('ssl:myserver:1234', '/baz/zyz', '456', 'myname', 'p4ssw0rd')


def test_split_url():
    assert split_url(url1, {}) == parts1
    assert split_url(url2, {}) == parts2


def test_join_url():
    assert join_url(*parts1[:2]) == "p4://perforce:1666/foo/bar"
    assert join_url(*parts2[:2]) == "p4://myserver:1234/baz/zyz"
