.. note::

    This section of the documentation is currently out of date.

    pip developers welcome your help to update this documentation. If
    you're interested in helping out, please let us know in the
    `tracking issue`_, or just submit a pull request and mention it in
    that tracking issue.

.. _`tracking issue`: https://github.com/pypa/pip/issues/7279

======================
Continuous Integration
======================

Supported interpreters
======================

pip support a variety of Python interpreters:

- CPython 3.6
- CPython 3.7
- CPython 3.8
- Latest PyPy3

on different operating systems:

- Linux
- Windows
- MacOS

and on different architectures:

- x64
- x86

so 42 hypothetical interpreters.


Checks
======

``pip`` CI runs different kind of tests:

- lint (defined in ``.pre-commit-config.yaml``)
- docs
- vendoring (is the ``src/_internal/_vendor`` directory cleanly vendored)
- unit tests (present in ``tests/unit``)
- "integration" tests (mostly present in ``tests/functional``)
- package (test the packaging steps)

Since lint, docs, vendoring and package tests only need to run on a pip
developer/contributor machine, they only need to be tested on the x64 variant
of the 3 different operating systems, and when an interpreter needs to be
specified it's ok to require the latest CPython interpreter.

So only unit tests and integration tests would need to be run with the different
interpreters.


Services
========

pip test suite and checks are distributed on three different platforms that
provides free executors for open source packages:

- `GitHub Actions`_ (Used for code quality and development tasks)
- `Azure DevOps CI`_ (Used for tests)
- `Travis CI`_ (Used for PyPy tests)

.. _`Travis CI`: https://travis-ci.org/
.. _`Azure DevOps CI`: https://azure.microsoft.com/en-us/services/devops/
.. _`GitHub Actions`: https://github.com/features/actions


Current run tests
=================

Developer tasks
---------------

======== =============== ================ ================== =============
   OS          docs            lint           vendoring        packaging
======== =============== ================ ================== =============
Linux     Travis, Github  Travis, Github    Travis, Github       Azure
Windows       Github           Github           Github           Azure
MacOS         Github           Github           Github           Azure
======== =============== ================ ================== =============

Actual testing
--------------

+------------------------------+---------------+-----------------+
|       **interpreter**        |   **unit**    | **integration** |
+-----------+----------+-------+---------------+-----------------+
|           |          +-------+---------------+-----------------+
|           |          | CP3.6 |   Azure       |                 |
|           |          +-------+---------------+-----------------+
|           |   x86    | CP3.7 |   Azure       |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.8 |   Azure       |                 |
|           |          +-------+---------------+-----------------+
|           |          | PyPy3 |               |                 |
|  Windows  +----------+-------+---------------+-----------------+
|           |          | CP3.6 |   Azure       |                 |
|           |          +-------+---------------+-----------------+
|           |   x64    | CP3.7 |   Azure       |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.8 |   Azure       |   Azure         |
|           |          +-------+---------------+-----------------+
|           |          | PyPy3 |               |                 |
+-----------+----------+-------+---------------+-----------------+
|           |          | CP3.6 |               |                 |
|           |          +-------+---------------+-----------------+
|           |   x86    | CP3.7 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.8 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | PyPy3 |               |                 |
|   Linux   +----------+-------+---------------+-----------------+
|           |          | CP3.6 |   Azure       |   Azure         |
|           |          +-------+---------------+-----------------+
|           |   x64    | CP3.7 |   Azure       |   Azure         |
|           |          +-------+---------------+-----------------+
|           |          | CP3.8 |   Azure       |   Azure         |
|           |          +-------+---------------+-----------------+
|           |          | PyPy3 |   Travis      |   Travis        |
+-----------+----------+-------+---------------+-----------------+
|           |          | CP3.6 |               |                 |
|           |          +-------+---------------+-----------------+
|           |   x86    | CP3.7 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.8 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | PyPy3 |               |                 |
|   MacOS   +----------+-------+---------------+-----------------+
|           |          | CP3.6 |   Github      |   Github        |
|           |          +-------+---------------+-----------------+
|           |   x64    | CP3.7 |   Github      |   Github        |
|           |          +-------+---------------+-----------------+
|           |          | CP3.8 |   Github      |   Github        |
|           |          +-------+---------------+-----------------+
|           |          | PyPy3 |               |                 |
+-----------+----------+-------+---------------+-----------------+
