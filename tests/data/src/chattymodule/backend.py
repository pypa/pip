import os
import sys

from setuptools import build_meta
from setuptools.build_meta import *


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    if config_settings and "fail" in config_settings:
        print("I DIE, I DIE in prepare_metadata_for_build_wheel")
        sys.exit(1)
    print("HELLO FROM CHATTYMODULE prepare_metadata_for_build_wheel")
    return build_meta.prepare_metadata_for_build_wheel(
        metadata_directory, config_settings
    )


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    if config_settings and "fail" in config_settings:
        print("I DIE, I DIE in build_wheel")
        sys.exit(1)
    print("HELLO FROM CHATTYMODULE build_wheel")
    return build_meta.build_wheel(wheel_directory, config_settings, metadata_directory)
