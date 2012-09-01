import codecs
import os
import re
import sys
from setuptools import setup


def read(*parts):
    return codecs.open(os.path.join(os.path.abspath(os.path.dirname(__file__)), *parts), 'r').read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

long_description = """

The main website for pip is `www.pip-installer.org
<http://www.pip-installer.org>`_. You can also install
the `in-development version <https://github.com/pypa/pip/tarball/develop#egg=pip-dev>`_
of pip with ``easy_install pip==dev``.

"""
# remove the toctree from sphinx index, as it breaks long_description
parts = read("docs", "index.txt").split("split here", 2)
long_description = (parts[0] + long_description + parts[2] +
                    "\n\n" + read("docs", "news.txt"))

setup(name="pip",
      version=find_version('pip', '__init__.py'),
      description="pip installs packages. Python packages. An easy_install replacement",
      long_description=long_description,
      classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Build Tools',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
      ],
      keywords='easy_install distutils setuptools egg virtualenv',
      author='The pip developers',
      author_email='python-virtualenv@groups.google.com',
      url='http://www.pip-installer.org',
      license='MIT',
      packages=['pip', 'pip.commands', 'pip.vcs'],
      entry_points=dict(console_scripts=['pip=pip:main', 'pip-%s=pip:main' % sys.version[:3]]),
      test_suite='nose.collector',
      tests_require=['nose', 'virtualenv>=1.7', 'scripttest>=1.1.1', 'mock'],
      zip_safe=False)
