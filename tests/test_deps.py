# -*- coding: utf-8 -*-

import os
from unittest import TestCase
from tests.test_pip import reset_env, run_pip, here


def _run_deps(*args, **kwargs):
    kwargs['expect_stderr'] = True
    find_links = 'file://' + os.path.join(here, 'packages/deps')
    return run_pip('deps', '--no-index', '-f', find_links, *args, **kwargs)


class TestDepsCommandWithASinglePackage(TestCase):

    @classmethod
    def setupClass(cls):
        reset_env()
        cls.result = _run_deps('dependency')

    def test_returns_version_info(self):
        self.assertTrue('dependency==1.0' in self.result.stdout)

    def test_redirects_downloading_messages_to_stderr(self):
        self.assertTrue('Downloading/unpacking' in self.result.stderr)


def test_deps_command_returns_info_for_a_package_with_dependencies():
    reset_env()
    result = _run_deps('dependant')
    assert 'dependant==1.0' in result.stdout
    assert 'dependency==1.0' in result.stdout

