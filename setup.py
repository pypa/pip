import sys
import os
from setuptools import setup

version = "0.7.1"

doc_dir = os.path.join(os.path.dirname(__file__), 'docs')
index_filename = os.path.join(doc_dir, 'index.txt')
long_description = """\
The main website for pip is `pip.openplans.org
<http://pip.openplans.org>`_.  You can also install
the `in-development version <http://bitbucket.org/ianb/pip/get/tip.gz#egg=pip-dev>`_
of pip with ``easy_install pip==dev``.
"""
long_description = long_description + open(index_filename).read().split('split here', 1)[1]

setup(name='pip',
      version=version,
      description="pip installs packages.  Python packages.  An easy_install replacement",
      long_description=long_description,
      classifiers=[
        'Development Status :: 4 - Beta',
        #'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Build Tools',
        'Programming Language :: Python :: 2.4',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
      ],
      keywords='easy_install distutils setuptools egg virtualenv',
      author='Ian Bicking',
      author_email='python-virtualenv@groups.google.com',
      url='http://pip.openplans.org',
      license='MIT',
      packages=['pip', 'pip.commands', 'pip.vcs'],
      entry_points=dict(console_scripts=['pip=pip:main', 'pip-%s=pip:main' % sys.version[:3]]),
      test_suite='nose.collector',
      tests_require=['nose', 'virtualenv', 'scripttest', 'mock'],
      zip_safe=False)
