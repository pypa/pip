.. _`pip show`:

pip show
--------

.. contents::


Usage
*****

.. pip-command-usage:: show


Description
***********

.. pip-command-description:: show


Options
*******

.. pip-command-options:: show


Examples
********

#. Show information about a package:

    ::

      $ pip show sphinx
      Name: Sphinx
      Version: 1.4.5
      Summary: Python documentation generator
      Home-page: http://sphinx-doc.org/
      Author: Georg Brandl
      Author-email: georg@python.org
      License: BSD
      Location: /my/env/lib/python2.7/site-packages
      Requires: docutils, snowballstemmer, alabaster, Pygments, imagesize, Jinja2, babel, six

#. Show all information about a package

    ::

      $ pip show --verbose sphinx
      Name: Sphinx
      Version: 1.4.5
      Summary: Python documentation generator
      Home-page: http://sphinx-doc.org/
      Author: Georg Brandl
      Author-email: georg@python.org
      License: BSD
      Location: /my/env/lib/python2.7/site-packages
      Requires: docutils, snowballstemmer, alabaster, Pygments, imagesize, Jinja2, babel, six
      Metadata-Version: 2.0
      Installer:
      Classifiers:
        Development Status :: 5 - Production/Stable
        Environment :: Console
        Environment :: Web Environment
        Intended Audience :: Developers
        Intended Audience :: Education
        License :: OSI Approved :: BSD License
        Operating System :: OS Independent
        Programming Language :: Python
        Programming Language :: Python :: 2
        Programming Language :: Python :: 3
        Framework :: Sphinx
        Framework :: Sphinx :: Extension
        Framework :: Sphinx :: Theme
        Topic :: Documentation
        Topic :: Documentation :: Sphinx
        Topic :: Text Processing
        Topic :: Utilities
      Entry-points:
        [console_scripts]
        sphinx-apidoc = sphinx.apidoc:main
        sphinx-autogen = sphinx.ext.autosummary.generate:main
        sphinx-build = sphinx:main
        sphinx-quickstart = sphinx.quickstart:main
        [distutils.commands]
        build_sphinx = sphinx.setup_command:BuildDoc
