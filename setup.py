import sys
if sys.platform == 'win32' or 'upload' in sys.argv:
    from setuptools import setup
else:
    from distutils.core import setup
import os


version = '0.6'

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
      py_modules=['pip'],
      **kw)
      
