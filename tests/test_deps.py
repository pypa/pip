# -*- coding: utf-8 -*-

import os
from unittest import TestCase
from tests.test_pip import reset_env, run_pip, here
from pip.basecommand import ERROR, SUCCESS


def _run_local_deps(*args, **kwargs):
    find_links = 'file://' + os.path.join(here, 'packages/deps')
    return _run_deps('-f', find_links, *args, **kwargs)

def _run_deps(*args, **kwargs):
    kwargs['expect_stderr'] = True
    return run_pip('deps', '--no-index', *args, **kwargs)


class TestDepsCommandWithASinglePackage(TestCase):

    @classmethod
    def setupClass(cls):
        reset_env()
        cls.result = _run_local_deps('dependency')

    def test_exits_with_success(self):
        self.assertEqual(self.result.returncode, SUCCESS)

    def test_returns_version_info(self):
        self.assertTrue('dependency==1.0' in self.result.stdout)

    def test_redirects_downloading_messages_to_stderr(self):
        self.assertTrue('Downloading/unpacking' in self.result.stderr)

    def test_removes_downloaded_files(self):
        self.assertFalse(self.result.files_created)


class TestDepsCommandWithDependencies(TestCase):

    @classmethod
    def setupClass(cls):
        reset_env()
        cls.result = _run_local_deps('dependant')

    def test_returns_version_info(self):
        assert 'dependant==1.0' in self.result.stdout
        assert 'dependency==1.0' in self.result.stdout

    def test_exits_with_success(self):
        self.assertEqual(self.result.returncode, SUCCESS)


class TestDepsCommandWithNonExistentPackage(TestCase):

    @classmethod
    def setupClass(cls):
        reset_env()
        cls.result = _run_local_deps('non-existent', expect_error=True)

    def test_exits_with_error(self):
        self.assertEqual(self.result.returncode, ERROR)


class TestDepsWithURL(TestCase):

    @classmethod
    def setupClass(cls):
        reset_env()
        path = os.path.join(here, 'packages/deps/dependency-1.0.tar.gz')
        cls.url = 'file://' + path
        cls.result = _run_deps(cls.url)

    def test_returns_dependency_url(self):
        assert self.url in self.result.stdout

    def test_exits_with_success(self):
        self.assertEqual(self.result.returncode, SUCCESS)


class TestDepsWithDependencyLinks(TestCase):

    @classmethod
    def setupClass(cls):
        reset_env()
        cls.result = _run_local_deps('dependency-links')

    def test_returns_dependency_links(self):
        assert 'dependency-links==1.0' in self.result.stdout
        assert '--find-links http://pypi.python.org/simple' in self.result.stdout

    def test_exits_with_success(self):
        self.assertEqual(self.result.returncode, SUCCESS)
