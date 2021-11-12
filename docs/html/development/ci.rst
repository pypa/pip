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

- CPython 3.7
- CPython 3.8
- CPython 3.9
- CPython 3.10
- Latest PyPy3

on different operating systems:

- Linux
- Windows
- macOS

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

pip test suite and checks are distributed on `GitHub Actions`_ which provides
free executors for open source packages.

.. _`GitHub Actions`: https://github.com/features/actions


Current run tests
=================

Developer tasks
---------------

======== =============== ================ ================== =============
   OS          docs            lint           vendoring        packaging
======== =============== ================ ================== =============
Linux         GitHub           GitHub           GitHub           GitHub
Windows       GitHub           GitHub           GitHub           GitHub
macOS         GitHub           GitHub           GitHub           GitHub
======== =============== ================ ================== =============

Actual testing
--------------

+------------------------------+---------------+-----------------+
|       **interpreter**        |   **unit**    | **integration** |
+-----------+----------+-------+---------------+-----------------+
|           |   x86    | CP3.7 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.8 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.9 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.10|               |                 |
|           |          +-------+---------------+-----------------+
|           |          | PyPy3 |               |                 |
|  Windows  +----------+-------+---------------+-----------------+
|           |   x64    | CP3.7 |   GitHub      |   GitHub        |
|           |          +-------+---------------+-----------------+
|           |          | CP3.8 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.9 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.10|   GitHub      |   GitHub        |
|           |          +-------+---------------+-----------------+
|           |          | PyPy3 |               |                 |
+-----------+----------+-------+---------------+-----------------+
|           |   x86    | CP3.7 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.8 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.9 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | PyPy3 |               |                 |
|   Linux   +----------+-------+---------------+-----------------+
|           |   x64    | CP3.7 |   GitHub      |   GitHub        |
|           |          +-------+---------------+-----------------+
|           |          | CP3.8 |   GitHub      |   GitHub        |
|           |          +-------+---------------+-----------------+
|           |          | CP3.9 |   GitHub      |   GitHub        |
|           |          +-------+---------------+-----------------+
|           |          | CP3.10|   GitHub      |   GitHub        |
|           |          +-------+---------------+-----------------+
|           |          | PyPy3 |               |                 |
+-----------+----------+-------+---------------+-----------------+
|           |  arm64   | CP3.7 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.8 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.9 |               |                 |
|           |          +-------+---------------+-----------------+
|           |          | CP3.10|               |                 |
|           |          +-------+---------------+-----------------+
|           |          | PyPy3 |               |                 |
|   macOS   +----------+-------+---------------+-----------------+
|           |   x64    | CP3.7 |   GitHub      |   GitHub        |
|           |          +-------+---------------+-----------------+
|           |          | CP3.8 |   GitHub      |   GitHub        |
|           |          +-------+---------------+-----------------+
|           |          | CP3.9 |   GitHub      |   GitHub        |
|           |          +-------+---------------+-----------------+
|           |          | CP3.10|   GitHub      |   GitHub        |
|           |          +-------+---------------+-----------------+
|           |          | PyPy3 |               |                 |
+-----------+----------+-------+---------------+-----------------+
