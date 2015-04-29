import os
import tempfile

import pytest

from pip.download import path_to_url
from pip.req.req_install import InstallRequirement
from pip.req.req_cache import RequirementCache, CachedRequirement
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


def test_add_not_entered(data):
    cache = RequirementCache()
    src = path_to_url(str(data.src + '/requires_simple'))
    req = CachedRequirement(url=src)
    with pytest.raises(AssertionError):
        cache.add(req)
    with cache:
        cache.add(req)
    with pytest.raises(AssertionError):
        cache.add(req)


def test_add_path_req(data):
    cache = RequirementCache()
    src = path_to_url(str(data.src + '/requires_simple'))
    req = CachedRequirement(url=src)
    with cache:
        cache.add(req)
        assert req == cache.lookup_url(src)
        with pytest.raises(ValueError):
            cache.add(req)


def test_add_vcs_req():
    cache = RequirementCache()
    src = 'git+git://github.com/pypa/pip-test-package'
    req = CachedRequirement(url=src)
    with cache:
        cache.add(req)
        assert req == cache.lookup_url(src)
        with pytest.raises(ValueError):
            cache.add(req)


def test_add_editable_vcs_req_no_src_dir():
    cache = RequirementCache()
    src = 'git+git://github.com/pypa/pip-test-package'
    req = CachedRequirement(url=src, editable=True)
    with cache:
        with pytest.raises(AssertionError):
            cache.add(req)


def test_add_editable_vcs_req():
    src = tempfile.mkdtemp()
    cache = RequirementCache(src_dir=src)
    src_url = 'git+git://github.com/pypa/pip-test-package'
    req = CachedRequirement(
        url=src_url, editable=True, name='pip-test-package')
    try:
        with cache:
            cache.add(req)
            assert req == cache.lookup_url(src_url)
            with pytest.raises(ValueError):
                cache.add(req)
    finally:
        rmtree(src)


def test_add_named_req():
    cache = RequirementCache()
    req = CachedRequirement(name='simple', version='1.0')
    with cache:
        cache.add(req)
        assert req == cache.lookup_name(name="simple", version="1.0")
        with pytest.raises(ValueError):
            cache.add(req)


def test_lookup_missing():
    cache = RequirementCache()
    req = CachedRequirement(name="simple", version="2.0")
    with cache:
        cache.add(req)
        with pytest.raises(KeyError):
            cache.lookup_url("file:///home/dir")
        with pytest.raises(KeyError):
            cache.lookup_name("simple", "1.0")


def test_build_path_not_in_cache():
    cache = RequirementCache()
    req = CachedRequirement(name='fred', version='1.0')
    with cache:
        with pytest.raises(KeyError):
            cache.build_path(req)


def test_build_path_editable_remote_name_known():
    src = tempfile.mkdtemp()
    cache = RequirementCache(src_dir=src)
    req = CachedRequirement(
        url='git+git://github.com/pypa/pip-test-package',
        name='pip-test-package',
        editable=True)
    try:
        with cache:
            cache.add(req)
            path = cache.build_path(req)
            assert path == cache.src_dir + os.path.sep + 'pip-test-package'
            assert os.path.exists(path)
    finally:
        rmtree(src)


def test_build_path_editable_remote_no_name():
    src = tempfile.mkdtemp()
    cache = RequirementCache(src_dir=src)
    req = CachedRequirement(
        url='git+git://github.com/pypa/pip-test-package',
        editable=True)
    try:
        with cache:
            with pytest.raises(ValueError):
                cache.add(req)
    finally:
        rmtree(src)


def test_build_path_remote():
    cache = RequirementCache()
    req = CachedRequirement(url='git+git://github.com/pypa/pip-test-package')
    with cache:
        cache.add(req)
        path = cache.build_path(req)
        assert path.startswith(cache.path), cache
        assert os.path.exists(path)


def test_build_path_local_editable(data):
    cache = RequirementCache()
    src = str(data.src + '/requires_simple')
    src_url = path_to_url(src)
    req = CachedRequirement(url=src_url, editable=True)
    with cache:
        cache.add(req)
        path = cache.build_path(req)
        assert path == src


def test_build_path_local(data):
    cache = RequirementCache()
    src = path_to_url(str(data.src + '/requires_simple'))
    req = CachedRequirement(url=src)
    with cache:
        cache.add(req)
        path = cache.build_path(req)
        assert path.startswith(cache.path), cache


def test_build_path_named_req():
    cache = RequirementCache()
    req = CachedRequirement(name='simple', version='1.0')
    with cache:
        cache.add(req)
        path = cache.build_path(req)
        assert path.startswith(cache.path), cache
