===============
Getting Started
===============

We’re pleased that you are interested in working on pip.

This document is meant to get you setup to work on pip and to act as a guide and
reference to the development setup. If you face any issues during this
process, please `open an issue`_ about it on the issue tracker.


Get the source code
===================

To work on pip, you first need to get the source code of pip. The source code is
available on `GitHub`_.

.. code-block:: console

    $ git clone https://github.com/pypa/pip
    $ cd pip


Development Environment
=======================

pip is a command line application written in Python. For developing pip,
you should `install Python`_ on your computer.

For developing pip, you need to install :pypi:`tox`. Often, you can run
``python -m pip install tox`` to install and use it.


Running pip From Source Tree
============================

To run the pip executable from your source tree during development, install pip
locally using editable installation (inside a virtualenv).
You can then invoke your local source tree pip normally.

.. tab:: Unix/macOS

    .. code-block:: shell

        virtualenv venv # You can also use "python -m venv venv" from python3.3+
        source venv/bin/activate
        python -m pip install -e .
        python -m pip --version

.. tab:: Windows

    .. code-block:: shell

        virtualenv venv # You can also use "py -m venv venv" from python3.3+
        venv\Scripts\activate
        py -m pip install -e .
        py -m pip --version

Running Tests
=============

pip's tests are written using the :pypi:`pytest` test framework and
:mod:`unittest.mock`. :pypi:`tox` is used to automate the setup and execution
of pip's tests.

It is preferable to run the tests in parallel for better experience during development,
since the tests can take a long time to finish when run sequentially.

To run tests:

.. code-block:: console

    $ tox -e py36 -- -n auto

To run tests without parallelization, run:

.. code-block:: console

    $ tox -e py36

The example above runs tests against Python 3.6. You can also use other
versions like ``py39`` and ``pypy3``.

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
===============

pip uses :pypi:`pre-commit` for managing linting of the codebase.
``pre-commit`` performs various checks on all files in pip and uses tools that
help follow a consistent code style within the codebase.

To use linters locally, run:

.. code-block:: console

    $ tox -e lint

.. note::

    Avoid using ``# noqa`` comments to suppress linter warnings - wherever
    possible, warnings should be fixed instead. ``# noqa`` comments are
    reserved for rare cases where the recommended style causes severe
    readability problems.


Building Documentation
======================

pip's documentation is built using :pypi:`Sphinx`. The documentation is written
in reStructuredText.

To build it locally, run:

.. code-block:: console

    $ tox -e docs

The built documentation can be found in the ``docs/build`` folder.

For each Pull Request made the documentation is deployed following this link:

.. code-block:: none

    https://pip--<PR-NUMBER>.org.readthedocs.build/en/<PR-NUMBER>


What Next?
==========

The following pages may be helpful for new contributors on where to look next
in order to start contributing.

* Some `good first issues`_ on GitHub for new contributors
* A deep dive into `pip's architecture`_
* A guide on `triaging issues`_ for issue tracker
* Getting started with Git

  - `Hello World for Git`_
  - `Understanding the GitHub flow`_
  - `Start using Git on the command line`_


.. _`open an issue`: https://github.com/pypa/pip/issues/new?title=Trouble+with+pip+development+environment
.. _`install Python`: https://realpython.com/installing-python/
.. _`PEP 484 type-comments`: https://www.python.org/dev/peps/pep-0484/#suggested-syntax-for-python-2-7-and-straddling-code
.. _`rich CLI`: https://docs.pytest.org/en/latest/usage.html#specifying-tests-selecting-tests
.. _`GitHub`: https://github.com/pypa/pip
.. _`good first issues`: https://github.com/pypa/pip/labels/good%20first%20issue
.. _`pip's architecture`: https://pip.pypa.io/en/latest/development/architecture/
.. _`triaging issues`: https://pip.pypa.io/en/latest/development/issue-triage/
.. _`Hello World for Git`: https://guides.github.com/activities/hello-world/
.. _`Understanding the GitHub flow`: https://guides.github.com/introduction/flow/
.. _`Start using Git on the command line`: https://docs.gitlab.com/ee/gitlab-basics/start-using-git.html
