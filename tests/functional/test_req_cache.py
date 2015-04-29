import os
import tempfile

from pip.req.req_cache import RequirementCache
from pip.utils import rmtree


def test_noargs_valid():
    cache = RequirementCache()
    with cache:
        assert cache.path is not None


def test_src_dir_preserved():
    src = tempfile.mkdtemp()
    cache = RequirementCache(src_dir=src)
    try:
        with cache:
            path = cache.src_dir + '/test'
            os.makedirs(path)
        assert os.path.exists(path)
    finally:
        rmtree(src)
