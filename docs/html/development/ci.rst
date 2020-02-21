.. note::

    This section of the documentation is currently being written. pip
    developers welcome your help to complete this documentation. If you're
    interested in helping out, please let us know in the `tracking issue`_.

.. _`tracking issue`: https://github.com/pypa/pip/issues/7279

======================
Continuous Integration
======================

Supported interpreters
======================

pip support a variety of Python interpreters:

  - CPython 2.7
  - CPython 3.5
  - CPython 3.6
  - CPython 3.7
  - CPython 3.8
  - Latest PyPy
  - Latest PyPy3

on different operating systems:

  - Linux
  - Windows
  - MacOS

and on different architectures:

  - x64
  - x86

so 42 hypothetical combinations.


Checks
======

``pip`` CI runs various "checks":

- Development tooling
  - docs (does the documentation build correctly?)
  - lint (automated code quality checks, run with ``pre-commit``)
  - vendoring (is ``src/pip/_vendor`` correctly constructed?)
- Tests
  - unit tests (present in ``tests/unit``)
  - "integration" tests (mostly present in ``tests/functional``)
- Packaging (test the packaging steps)

We run development tooling checks on the latest CPython (x64), on every
OS. This helps ensure they'll also run on a pip developer/contributor's
machine regardless of the OS they use.

We try to run the tests on as many interpreter-OS-architecture
combinations as we can, without having a significant slowdown on our
productivity due to CI wait times.


Services
========

pip test suite and checks are distributed on three different platforms that
provides free executors for open source packages:

  - `Travis CI`_ (Used for Linux)
  - `Azure DevOps CI`_ (Linux, MacOS & Windows tests)
  - `GitHub Actions`_ (Linux, MacOS & Windows tests)

.. _`Travis CI`: https://travis-ci.org/
.. _`Azure DevOps CI`: https://azure.microsoft.com/en-us/services/devops/
.. _`GitHub Actions`: https://github.com/features/actions

TODO

- how many workers we get per-CI-service.
- add links to "most relevant resources" for each CI-service.
- describe how our runs are set up for short-circuiting on failures in
  linting / documentation / vendoring / unit tests / integration tests.


Current run tests
=================

Developer tasks
---------------

======== =============== ================ ================== ============
   OS          docs            lint           vendoring        packages
======== =============== ================ ================== ============
Linux     Travis, Github  Travis, Github    Travis, Github      Azure
Windows                                                         Azure
MacOS                                                           Azure
======== =============== ================ ================== ============

Actual testing
--------------

+------------------------------+---------------+-----------------+
|       **combination**        |   **unit**    | **integration** |
+-----------+----------+-------+---------------+-----------------+
|           |          | CP2.7 |   Azure       |   Azure         |
|           |          +-------+---------------+-----------------+
|           |          | CP3.5 |   Azure       |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.6 |   Azure       |                 |
|           |          +-------+---------------+-----------------+
|           |   x86    | CP3.7 |   Azure       |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.8 |   Azure       |                 |
|           |          +-------+---------------+-----------------+
|           |          | PyPy  |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | PyPy3 |               |                 |
|  Windows  +----------+-------+---------------+-----------------+
|           |          | CP2.7 |   Azure       |   Azure         |
|           |          +-------+---------------+-----------------+
|           |          | CP3.5 |   Azure       |   Azure         |
|           |          +-------+---------------+-----------------+
|           |          | CP3.6 |   Azure       |   Azure         |
|           |          +-------+---------------+-----------------+
|           |   x64    | CP3.7 |   Azure       |   Azure         |
|           |          +-------+---------------+-----------------+
|           |          | CP3.8 |   Azure       |   Azure         |
|           |          +-------+---------------+-----------------+
|           |          | PyPy  |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | PyPy3 |               |                 |
+-----------+----------+-------+---------------+-----------------+
|           |          | CP2.7 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.5 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.6 |               |                 |
|           |          +-------+---------------+-----------------+
|           |   x86    | CP3.7 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.8 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | PyPy  |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | PyPy3 |               |                 |
|   Linux   +----------+-------+---------------+-----------------+
|           |          | CP2.7 | Travis,Azure  |  Travis,Azure   |
|           |          +-------+---------------+-----------------+
|           |          | CP3.5 | Travis,Azure  |  Travis,Azure   |
|           |          +-------+---------------+-----------------+
|           |          | CP3.6 | Travis,Azure  |  Travis,Azure   |
|           |          +-------+---------------+-----------------+
|           |   x64    | CP3.7 | Travis,Azure  |  Travis,Azure   |
|           |          +-------+---------------+-----------------+
|           |          | CP3.8 |   Travis      |   Travis        |
|           |          +-------+---------------+-----------------+
|           |          | PyPy  |   Travis      |   Travis        |
|           |          +-------+---------------+-----------------+
|           |          | PyPy3 |   Travis      |   Travis        |
+-----------+----------+-------+---------------+-----------------+
|           |          | CP2.7 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.5 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.6 |               |                 |
|           |          +-------+---------------+-----------------+
|           |   x86    | CP3.7 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.8 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | PyPy  |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | PyPy3 |               |                 |
|   MacOS   +----------+-------+---------------+-----------------+
|           |          | CP2.7 |   Azure       |   Azure         |
|           |          +-------+---------------+-----------------+
|           |          | CP3.5 |   Azure       |   Azure         |
|           |          +-------+---------------+-----------------+
|           |          | CP3.6 |   Azure       |   Azure         |
|           |          +-------+---------------+-----------------+
|           |   x64    | CP3.7 |   Azure       |   Azure         |
|           |          +-------+---------------+-----------------+
|           |          | CP3.8 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | PyPy  |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | PyPy3 |               |                 |
+-----------+----------+-------+---------------+-----------------+
