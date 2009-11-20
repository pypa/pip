import sys
force_setuptools = False
if 'upload' in sys.argv or 'develop' in sys.argv:
    force_setuptools = True
if sys.platform == 'win32':
    force_setuptools = True
if force_setuptools:
    from setuptools import setup
else:
    from distutils.core import setup
import os


version = "0.6.post1"

doc_dir = os.path.join(os.path.dirname(__file__), 'docs')
index_filename = os.path.join(doc_dir, 'index.txt')
long_description = """\ 
The main website for pip is `pip.openplans.org
<http://pip.openplans.org>`_.  You can also install
the `in-development version <http://bitbucket.org/ianb/pip/get/tip.gz#egg=pip-dev>`_ 
of pip with ``easy_install pip==dev``.
"""
long_description = long_description + open(index_filename).read().split('split here', 1)[1]

if sys.platform == 'win32':
    kw = dict(entry_points=dict(console_scripts=['pip=pip:main']))
else:
    kw = dict(scripts=['scripts/pip'])

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
      ],
      keywords='easy_install distutils setuptools egg virtualenv',
      author='The Open Planning Project',
      author_email='python-virtualenv@groups.google.com',
      url='http://pip.openplans.org',
      license='MIT',
      packages=['pip'],
      **kw)
      
