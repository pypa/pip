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

Pip is a command line application written in Python. For developing pip,
you should `install Python`_ on your computer.

You can use :pypi:`nox` to manage development environments, or install the
dependencies in your own virtual environment.

Using Nox
---------

Install Nox in a virtual environment:

.. tab:: Unix/macOS

    .. code-block:: shell

        python -m venv .venv
        source .venv/bin/activate
        python -m pip install nox

.. tab:: Windows

    .. code-block:: shell

        py -m venv .venv
        .venv\Scripts\activate
        py -m pip install nox

Nox installs each session's dependencies from ``pylock.dev.toml`` by default.

To try different dependency versions or use a platform outside the lock,
set ``PIP_NOX_USE_LOCK=0`` and use ``-N`` to create a fresh environment:

.. tab:: Unix/macOS

    .. code-block:: shell

        PIP_NOX_USE_LOCK=0 nox -N -s test-3.10

.. tab:: Windows

    .. code-block:: powershell

        $env:PIP_NOX_USE_LOCK = "0"
        nox -N -s test-3.10
        Remove-Item Env:PIP_NOX_USE_LOCK

Installing dependencies yourself
--------------------------------

To install the test, type-checking, lint and documentation dependencies together,
activate a virtual environment and run:

.. code-block:: shell

    python -m pip install --upgrade "pip>=26.3"
    python -m pip install --group pylock.dev.toml:dev --group pylock.dev.toml:build
    python -m pip install --no-build-isolation -e .

For an individual task, replace ``dev`` with ``test``, ``typecheck``, ``lint``
or ``docs``. Keep ``build`` to install the locked build backend.

Run tools directly in this environment:

.. list-table::
    :header-rows: 1

    * - Group
      - Command
    * - ``test``
      - ``python -m pytest -n auto``
    * - ``typecheck``
      - ``python -m mypy --config-file=tests/typing/pyproject.toml src/pip tests tools noxfile.py``
    * - ``lint``
      - ``pre-commit run --all-files``
    * - ``docs``
      - ``python -m sphinx -W -t html -c docs/html -b html docs/html docs/build/html``

Before running tests directly, populate the test wheel cache:

.. code-block:: shell

    python -m pip wheel --wheel-dir tests/data/common_wheels --group pylock.dev.toml:test-common-wheels

Remove ``tests/data/common_wheels`` before rebuilding it with different versions;
the tests expect one wheel per package. Nox manages this cache automatically.

For unlocked dependencies, use ``python -m pip install --group dev`` and
``python -m pip install -e .`` instead.

Updating the locks
------------------

After changing dependencies, regenerate the development and script locks with:

.. code-block:: shell

    python -m nox -s lock

This uses Nab to update ``pylock.dev.toml`` and
``tools/pylock.update-rtd-redirects.toml``. CI checks that both locks match
their dependency declarations.


Running pip From Source Tree
============================

To run the pip executable from your source tree during development, install pip
locally using editable installation (inside a virtualenv).
You can then invoke your local source tree pip normally (be sure virtualenv is active).

.. tab:: Unix/macOS

    .. code-block:: shell

        python -m pip install -e .
        python -m pip --version

.. tab:: Windows

    .. code-block:: shell

        py -m pip install -e .
        py -m pip --version

Running Tests
=============

Pip's tests are written using the :pypi:`pytest` test framework and
:mod:`unittest.mock`. :pypi:`nox` is used to automate the setup and execution
of pip's tests.

It is preferable to run the tests in parallel for a better experience during development,
since the tests can take a long time to finish when run sequentially.

To run tests:

.. code-block:: console

    $ nox -s test-3.10 -- -n auto

To run tests without parallelization, run:

.. code-block:: console

    $ nox -s test-3.10

The example above runs tests against Python 3.10. You can also use other
versions like ``3.15`` and ``pypy3``. The PyPy test toolchain requires PyPy 3.11
because the current cryptography dependency does not support PyPy 3.10.

``nox`` has been configured to forward any additional arguments it is given to
``pytest``. This enables the use of pytest's `rich CLI`_. As an example, you
can select tests using the various ways that pytest provides:

.. code-block:: console

    $ # Using file name
    $ nox -s test-3.10 -- tests/functional/test_install.py
    $ # Using markers
    $ nox -s test-3.10 -- -m unit
    $ # Using keywords
    $ nox -s test-3.10 -- -k "install and not wheel"

.. note::

    When running pip's tests with OS distribution Python versions, be aware that some
    functional tests may fail due to potential patches introduced by the distribution.
    For all tests to pass consider:

    - Installing Python from `python.org`_ or compile from source
    - Or, using `pyenv`_ to assist with source compilation

Running pip's entire test suite requires supported version control tools
(subversion, bazaar, git, and mercurial) to be installed. If you are missing
any of these VCS, those tests should be skipped automatically. You can also
explicitly tell pytest to skip those tests:

.. code-block:: console

    $ nox -s test-3.10 -- -k "not svn"
    $ nox -s test-3.10 -- -k "not (svn or git)"

.. _python.org: https://www.python.org/downloads/
.. _pyenv: https://github.com/pyenv/pyenv


Running Linters
===============

Pip uses :pypi:`pre-commit` for managing linting of the codebase.
``pre-commit`` performs various checks on all files in pip and uses tools that
help follow a consistent code style within the codebase.

To use linters locally, run:

.. code-block:: console

    $ nox -s lint

.. note::

    Avoid using ``# noqa`` comments to suppress linter warnings - wherever
    possible, warnings should be fixed instead. ``# noqa`` comments are
    reserved for rare cases where the recommended style causes severe
    readability problems.


Running pip under a debugger
============================

In order to debug pip's behavior, you can run it under a debugger like so:

.. code-block:: console

    $ python -m pdb -m pip --debug ...

On Python 3.10, run the script from your pip checkout instead:

.. code-block:: console

    $ python -m pdb src/pip/__main__.py --debug ...


Replace the ``...`` with arguments you'd like to run pip with. Give PDB the
``c`` ("continue") command afterwards, to run the process.

The ``--debug`` flag disables pip's exception handler, which would normally
catch all unhandled exceptions. With this flag, pip will let these exceptions
propagate outside of its main subroutine, letting them get caught by the
debugger. This way you'll be able to debug an exception post-mortem via PDB.


Profiling pip
=============

Use ``cProfile`` to profile pip:

.. code-block:: console

    $ python -m cProfile -o pip.prof -m pip install ...

Omit ``-o pip.prof`` to print the results instead.

For the pure Python ``profile`` module, save the results and inspect them in a
separate process:

.. code-block:: console

    $ python -m profile -o pip.prof -m pip install ...
    $ python -m pstats pip.prof

Its default printed report imports ``pstats`` after installation, when pip
blocks new imports.


Building Documentation
======================

Pip's documentation is built using :pypi:`Sphinx`. The documentation is written
in reStructuredText.

To build it locally, run:

.. code-block:: console

    $ nox -s docs

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
.. _`rich CLI`: https://docs.pytest.org/en/latest/how-to/usage.html#specifying-which-tests-to-run
.. _`GitHub`: https://github.com/pypa/pip
.. _`good first issues`: https://github.com/pypa/pip/labels/good%20first%20issue
.. _`pip's architecture`: https://pip.pypa.io/en/latest/development/architecture/
.. _`triaging issues`: https://pip.pypa.io/en/latest/development/issue-triage/
.. _`Hello World for Git`: https://docs.github.com/en/get-started/start-your-journey/hello-world
.. _`Understanding the GitHub flow`: https://docs.github.com/en/get-started/using-github/github-flow
.. _`Start using Git on the command line`: https://docs.gitlab.com/topics/git/
