from setuptools import find_packages, setup


setup(
    name='LocalExtrasDuplicated',
    version='0.0.1',
    packages=find_packages(),
    extras_require={ 'shrubbery': ['LocalExtras[baz]']},
    install_requires=['simple', 'LocalExtras[bar]'],
)
