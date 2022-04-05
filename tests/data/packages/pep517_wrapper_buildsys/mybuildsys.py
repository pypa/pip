import os

from setuptools.build_meta import build_sdist
from setuptools.build_meta import build_wheel as setuptools_build_wheel
from setuptools.build_meta import (
    get_requires_for_build_sdist,
    get_requires_for_build_wheel,
    prepare_metadata_for_build_wheel,
)


def build_wheel(*a, **kw):
    if os.environ.get("PIP_TEST_FAIL_BUILD_WHEEL"):
        raise RuntimeError("Failing build_wheel, as requested.")

    # Create the marker file to record that the hook was called
    with open(os.environ["PIP_TEST_MARKER_FILE"], "wb"):
        pass

    return setuptools_build_wheel(*a, **kw)
