from pip._internal.vcs.helix_core import join_url, split_url

url1 = "p4+p4:///foo/bar"
url2 = "p4+ssl://myname:p4ssw0rd@myserver:1234/baz/zyz@456"


def test_parse_url():
    parts = split_url(url1, {})
    assert parts[0] == 'tcp:perforce:1666'
    assert parts[1] == '/foo/bar'
    assert parts[2] is None

    parts = split_url(url2, {})
    assert parts[0] == 'ssl:myserver:1234'
    assert parts[1] == '/baz/zyz'
    assert parts[2] == '456'
    assert parts[3] == 'myname'
    assert parts[4] == 'p4ssw0rd'


def test_join_url():
    assert join_url(*split_url(url1, {})[:2]) == "p4://perforce:1666/foo/bar"
    assert join_url(*split_url(url2, {})[:2]) == "p4://myserver:1234/baz/zyz"
