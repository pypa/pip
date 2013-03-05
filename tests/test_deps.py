# -*- coding: utf-8 -*-

import os
from tests.test_pip import reset_env, run_pip, here, mkdir


def test_should_run():
    reset_env()
    result = run_pip('deps', 'INITools==0.3', expect_stderr=True)

    assert 'INITools==0.3' in result.stdout

def test_should_direct_downloading_messages_to_stderr():
    reset_env()
    result = run_pip('deps', 'INITools==0.3', expect_stderr=True)

    assert 'Downloading/unpacking' in result.stderr
