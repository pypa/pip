import os

from setuptools import find_packages, setup


def path_to_url(path):
    """
    Convert a path to URI. The path will be made absolute and
    will not have quoted path parts.
    """
    path = os.path.normpath(os.path.abspath(path))
    drive, path = os.path.splitdrive(path)
    filepath = path.split(os.path.sep)
    url = "/".join(filepath)
    if drive:
        return "file:///" + drive + url
    return "file://" + url


setup(
    name="LocalEnvironMarker",
    version="0.0.1",
    packages=find_packages(),
    extras_require={
        ":python_version == '2.7'": ["simple"],
    },
)
