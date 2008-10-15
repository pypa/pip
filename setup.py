try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import os

version = '0.1.5'

doc_dir = os.path.join(os.path.dirname(__file__), 'docs')
index_filename = os.path.join(doc_dir, 'index.txt')
long_description = """\ 
The main website for pyinstall is `pyinstall.openplans.org
<http://pyinstall.openplans.org>`_

"""
long_description = long_description + open(index_filename).read().split('split here', 1)[1]



setup(name='pyinstall',
      version=version,
      description="Installer for Python packages",
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
      url='http://pyinstall.openplans.org',
      license='MIT',
      py_modules=['pyinstall'],
      ## FIXME: is this the best way?  (Works with distutils, but
      ## don't we really require setuptools anyway?)
      scripts=['pyinstall.py'],
      )
      
