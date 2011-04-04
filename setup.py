import codecs
import os
import sys

from setuptools import setup

# If you change this version, change it also in docs/conf.py
version = "1.0"
doc_dir = os.path.join(os.path.dirname(__file__), "docs")

def read(filename):
    if sys.version_info >= (3,):
        unicode = str
    filename = os.path.join(doc_dir, filename)
    return unicode(codecs.open(filename, encoding='utf-8').read())

long_description = """\
The main website for pip is `www.pip-installer.org
<http://www.pip-installer.org>`_.  You can also install
the `in-development version <https://github.com/pypa/pip/tarball/master#egg=pip-dev>`_
of pip with ``easy_install pip==dev``.
"""
long_description += read("index.txt").split("split here", 1)[1]
long_description += "\n\n" + read("news.txt")

setup(name="pip",
      version=version,
      description="pip installs packages. Python packages. An easy_install replacement",
      long_description=long_description,
      classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Build Tools',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.4',
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
      dependency_links=[
          'https://github.com/pypa/virtualenv/tarball/master#egg=virtualenv-1.5.2.post2',
          ],
      packages=['pip', 'pip.commands', 'pip.vcs'],
      entry_points=dict(console_scripts=['pip=pip:main', 'pip-%s=pip:main' % sys.version[:3]]),
      test_suite='nose.collector',
      tests_require=['nose', 'virtualenv==1.5.2.post2', 'scripttest==1.1.1', 'mock'],
      zip_safe=False)
