===============
Getting Started
===============

We’re pleased that you are interested in working on pip.

This document is meant to get you setup to work on pip and to act as a guide and
reference to the the development setup. If you face any issues during this
process, please `open an issue`_ about it on the issue tracker.

Development tools
=================

pip uses :pypi:`tox` for testing against multiple different Python environments
and ensuring reproducible environments for linting and building documentation.

For developing pip, you need to install ``tox`` on your system. Often, you can
just do ``python -m pip install tox`` to install and use it.

Running Tests
-------------

pip uses the :pypi:`pytest` test framework, :pypi:`mock` and :pypi:`pretend`
for testing. These are automatically installed by tox for running the tests.

To run tests locally, run:

.. code-block:: console

    $ tox -e py36

The example above runs tests against Python 3.6. You can also use other
versions like ``py27`` and ``pypy3``.

``tox`` has been configured to any additional arguments it is given to
``pytest``. This enables the use of pytest's `rich CLI`_. As an example, you
can select tests using the various ways that pytest provides:

.. code-block:: console

    $ # Using file name
    $ tox -e py36 -- tests/functional/test_install.py
    $ # Using markers
    $ tox -e py36 -- -m unit
    $ # Using keywords
    $ tox -e py36 -- -k "install and not wheel"

Running pip's test suite requires supported version control tools (subversion,
bazaar, git, and mercurial) to be installed. If you are missing one of the VCS
tools, you can tell pip to skip those tests:

.. code-block:: console

    $ tox -e py36 -- -k "not svn"
    $ tox -e py36 -- -k "not (svn or git)"

Running Linters
---------------

pip uses :pypi:`flake8` and :pypi:`isort` for linting the codebase. These
ensure that the codebase is in compliance with :pep:`8` and the imports are
consistently ordered and styled.

To use linters locally, run:

.. code-block:: console

    $ tox -e lint-py2
    $ tox -e lint-py3

The above commands run the linters on Python 2 followed by Python 3.

.. note::

    Do not silence errors from flake8 with ``# noqa`` comments or otherwise.
    The only exception to this is silencing unused-import errors for imports
    related to static type checking as currently `flake8 does not understand
    PEP 484 type-comments`_.

Running mypy
------------

pip uses :pypi:`mypy` to run static type analysis, which helps catch certain
kinds of bugs. The codebase uses `PEP 484 type-comments`_ due to compatibility
requirements with Python 2.7.

To run the ``mypy`` type checker, run:

.. code-block:: console

    $ tox -e mypy

Building Documentation
----------------------

pip's documentation is built using :pypi:`Sphinx`. The documentation is written
in reStructuredText.

To build it locally, run:

.. code-block:: console

    $ tox -e docs

The built documentation can be found in the ``docs/build`` folder.

.. _`open an issue`: https://github.com/pypa/pip/issues/new?title=Trouble+with+pip+development+environment
.. _`flake8 does not understand PEP 484 type-comments`: https://gitlab.com/pycqa/flake8/issues/118
.. _`PEP 484 type-comments`: https://www.python.org/dev/peps/pep-0484/#suggested-syntax-for-python-2-7-and-straddling-code
.. _`rich CLI`: https://docs.pytest.org/en/latest/usage.html#specifying-tests-selecting-tests
