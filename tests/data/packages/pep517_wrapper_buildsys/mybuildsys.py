import os

from setuptools.build_meta import build_sdist
from setuptools.build_meta import build_wheel as setuptools_build_wheel
from setuptools.build_meta import (get_requires_for_build_sdist,
                                   get_requires_for_build_wheel,
                                   prepare_metadata_for_build_wheel)


def build_wheel(*a, **kw):
    # Create the marker file to record that the hook was called
    with open(os.environ['PIP_TEST_MARKER_FILE'], 'wb'):
        pass

    return setuptools_build_wheel(*a, **kw)
