from pip.req.req_cache import RequirementCache


def test_noargs_valid():
    cache = RequirementCache()
    with cache:
        assert cache.path is not None
