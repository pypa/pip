import codecs
import os
import re
import sys
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    # intentionally *not* adding an encoding option to open
    # see here: https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    return codecs.open(os.path.join(here, *parts), 'r').read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

long_description = "\n" + "\n".join([read('PROJECT.txt'),
                                     read('docs', 'quickstart.rst')])

tests_require = ['nose>=1.3.0', 'virtualenv>=1.10', 'scripttest>=1.1.1', 'mock']

setup(name="pip",
      version=find_version('pip', '__init__.py'),
      description="A tool for installing and managing Python packages.",
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
          'Programming Language :: Python :: 3.3',
      ],
      keywords='easy_install distutils setuptools egg virtualenv',
      author='The pip developers',
      author_email='python-virtualenv@groups.google.com',
      url='http://www.pip-installer.org',
      license='MIT',
      packages=find_packages(exclude=["contrib", "docs", "tests*"]),
      package_data={'pip': ['*.pem']},
      entry_points=dict(console_scripts=['pip=pip:main', 'pip-%s=pip:main' % sys.version[:3]]),
      test_suite='nose.collector',
      tests_require=tests_require,
      zip_safe=False,
      extras_require={
          'testing': tests_require,
      })
