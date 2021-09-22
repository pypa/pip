.. _`pip show`:

========
pip show
========



Usage
=====

.. tab:: Unix/macOS

   .. pip-command-usage:: show "python -m pip"

.. tab:: Windows

   .. pip-command-usage:: show "py -m pip"


Description
===========

.. pip-command-description:: show


Options
=======

.. pip-command-options:: show


Format
======

The various fields present in the JSON output and their explanation is as follows.

*metadata*
   A dictionary with the core metadata fields present in the ``METADATA`` file,
   as defined in the `Core metadata specifications`_. We use the method detailed in
   `JSON-compatible Metadata`_ to convert core metadata to json. The fields are
   lower cased, with dashes replaced by underscores.

*direct_url*
   A dictionary containing the content of ``direct_url.json``,
   if present, as specified in :pep:`610`.

*installer*
   A string containing the content of ``INSTALLER``,
   if present, as specified in :pep:`376`.

*record*
   A list of ``[file_path, file_content_hash, file_size]``, representing
   the content of ``RECORD``, if present, as specified in :pep:`376`.

*requested*
   A string containing the content of ``REQUESTED``,
   if present, as specified in :pep:`376`.

*required_by*
   A list of canonicalized distribution names that depend
   on the queried distribution.

*requires*
   A list of canonicalized distribution names on which
   this distribution depends on.

*location*
   A string containing the path where the distribution is installed.
   This is the parent directory of the metadata (.dist-info or .egg-info) directory.

.. _`Core metadata specifications`: https://packaging.python.org/specifications/core-metadata/
.. _`JSON-compatible Metadata`: https://www.python.org/dev/peps/pep-0566/#json-compatible-metadata

Examples
========

#. Show information about a package in header format:

   .. tab:: Unix/macOS

      .. code-block:: console

         $ python -m pip show sphinx
         Name: Sphinx
         Version: 1.4.5
         Summary: Python documentation generator
         Home-page: http://sphinx-doc.org/
         Author: Georg Brandl
         Author-email: georg@python.org
         License: BSD
         Location: /my/env/lib/python2.7/site-packages
         Requires: docutils, snowballstemmer, alabaster, Pygments, imagesize, Jinja2, babel, six

   .. tab:: Windows

      .. code-block:: console

         C:\> py -m pip show sphinx
         Name: Sphinx
         Version: 1.4.5
         Summary: Python documentation generator
         Home-page: http://sphinx-doc.org/
         Author: Georg Brandl
         Author-email: georg@python.org
         License: BSD
         Location: /my/env/lib/python2.7/site-packages
         Requires: docutils, snowballstemmer, alabaster, Pygments, imagesize, Jinja2, babel, six

#. Show all information about a package in header format excluding files:

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

#. Show all information about a package in header format including files:

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
      Files:
          ../../../bin/sphinx-apidoc
          ../../../bin/sphinx-autogen
          ../../../bin/sphinx-build
          ../../../bin/sphinx-quickstart
          Sphinx-1.4.5.dist-info/DESCRIPTION.rst
          Sphinx-1.4.5.dist-info/INSTALLER
          Sphinx-1.4.5.dist-info/METADATA
          Sphinx-1.4.5.dist-info/RECORD
          Sphinx-1.4.5.dist-info/WHEEL
          Sphinx-1.4.5.dist-info/entry_points.txt
          Sphinx-1.4.5.dist-info/metadata.json
          Sphinx-1.4.5.dist-info/top_level.txt

   .. tab:: Unix/macOS

      .. code-block:: console

         $ python -m pip show --verbose sphinx
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

   .. tab:: Windows

      .. code-block:: console

         C:\> py -m pip show --verbose sphinx
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
