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
    name="LocalExtras",
    version="0.0.2",
    packages=find_packages(),
    install_requires=["simple==1.0"],
    extras_require={"bar": ["simple==2.0"], "baz": ["singlemodule"]},
)
