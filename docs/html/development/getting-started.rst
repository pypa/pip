===============
Getting Started
===============

We’re pleased that you are interested in working on pip.

This document is meant to get you setup to work on pip and to act as a guide and
reference to the the development setup. If you face any issues during this
process, please `open an issue`_ about it on the issue tracker.

Development Environment
-----------------------

pip is a command line application written in Python. For developing pip,
you should `install Python`_ on your computer.

For developing pip, you need to install :pypi:`tox`. Often, you can run
``python -m pip install tox`` to install and use it.

Running pip From Source Tree
----------------------------

To run the pip executable from your source tree during development, run pip
from the ``src`` directory:

.. code-block:: console

    $ python src/pip --version

Running Tests
-------------

pip's tests are written using the :pypi:`pytest` test framework, :pypi:`mock`
and :pypi:`pretend`. :pypi:`tox` is used to automate the setup and execution of
pip's tests.

To run tests locally, run:

.. code-block:: console

    $ tox -e py36

The example above runs tests against Python 3.6. You can also use other
versions like ``py27`` and ``pypy3``.

``tox`` has been configured to forward any additional arguments it is given to
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

pip uses :pypi:`pre-commit` for managing linting of the codebase.
``pre-commit`` performs various checks on all files in pip and uses tools that
help follow a consistent code style within the codebase.

To use linters locally, run:

.. code-block:: console

    $ tox -e lint

Building Documentation
----------------------

pip's documentation is built using :pypi:`Sphinx`. The documentation is written
in reStructuredText.

To build it locally, run:

.. code-block:: console

    $ tox -e docs

The built documentation can be found in the ``docs/build`` folder.

.. _`open an issue`: https://github.com/pypa/pip/issues/new?title=Trouble+with+pip+development+environment
.. _`install Python`: https://realpython.com/installing-python/
.. _`PEP 484 type-comments`: https://www.python.org/dev/peps/pep-0484/#suggested-syntax-for-python-2-7-and-straddling-code
.. _`rich CLI`: https://docs.pytest.org/en/latest/usage.html#specifying-tests-selecting-tests
