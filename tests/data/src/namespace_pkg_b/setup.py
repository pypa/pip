from setuptools import find_packages, setup

setup(
    name='namespace-pkg-b',
    version='1.0.0',
    packages=['namespace.pkg_b'],
    namespace_packages=['namespace']
)
