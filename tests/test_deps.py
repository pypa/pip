# -*- coding: utf-8 -*-

import os
from tests.test_pip import reset_env, run_pip, here, mkdir


def _run_deps(*args, **kwargs):
    reset_env()
    kwargs['expect_stderr'] = True
    find_links = 'file://' + os.path.join(here, 'packages/deps')
    return run_pip('deps', '--no-index', '-f', find_links, *args, **kwargs)

def test_deps_command_returns_info_for_a_single_package():
    result = _run_deps('dependency')
    assert 'dependency==1.0' in result.stdout

def test_deps_command_returns_info_for_a_package_with_dependencies():
    result = _run_deps('dependant')
    assert 'dependant==1.0' in result.stdout
    assert 'dependency==1.0' in result.stdout

def test_deps_command_redirects_downloading_messages_to_stderr():
    result = _run_deps('dependency')
    assert 'Downloading/unpacking' in result.stderr
