
.. _`pip download`:

pip download
------------

.. contents::

Usage
*****

.. pip-command-usage:: download


Description
***********

.. pip-command-description:: download


Overview
++++++++
``pip download`` replaces the ``--download`` option to ``pip install``,
which is now deprecated and will be removed in pip 10.

``pip download`` does the same resolution and downloading as ``pip install``,
but instead of installing the dependencies, it collects the downloaded
distributions into the directory provided (defaulting to the current
directory). This directory can later be passed as the value to ``pip install
--find-links`` to facilitate offline or locked down package installation.

``pip download`` with the ``--platform``, ``--python-version``,
``--implementation``, and ``--abi`` options provides the ability to fetch
dependencies for an interpreter and system other than the ones that pip is
running on. ``--only-binary=:all:`` is required when using any of these
options. It is important to note that these options all default to the
current system/interpreter, and not to the most restrictive constraints (e.g.
platform any, abi none, etc). To avoid fetching dependencies that happen to
match the constraint of the current interpreter (but not your target one), it
is recommended to specify all of these options if you are specifying one of
them. Generic dependencies (e.g. universal wheels, or dependencies with no
platform, abi, or implementation constraints) will still match an over-
constrained download requirement.



Options
*******

.. pip-command-options:: download

.. pip-index-options::


Examples
********

#. Download a package and all of its dependencies

    ::

      $ pip download SomePackage
      $ pip download -d . SomePackage  # equivalent to above
      $ pip download --no-index --find-links=/tmp/wheelhouse -d /tmp/otherwheelhouse SomePackage

#. Download a package and all of its dependencies with OSX specific interpreter constraints.
    This forces OSX 10.10 or lower compatibility. Since OSX deps are forward compatible,
    this will also match ``macosx-10_9_x86_64``, ``macosx-10_8_x86_64``, ``macosx-10_8_intel``,
    etc.
    It will also match deps with platform ``any``. Also force the interpreter version to ``27``
    (or more generic, i.e. ``2``) and implementation to ``cp`` (or more generic, i.e. ``py``).

    ::

      $ pip download \
          --only-binary=:all: \
          --platform macosx-10_10_x86_64 \
          --python-version 27 \
          --implementation cp \
          SomePackage

#. Download a package and its dependencies with linux specific constraints.
    Force the interpreter to be any minor version of py3k, and only accept
    ``cp34m`` or ``none`` as the abi.

    ::

      $ pip download \
          --only-binary=:all: \
          --platform linux_x86_64 \
          --python-version 3 \
          --implementation cp \
          --abi cp34m \
          SomePackage

#. Force platform, implementation, and abi agnostic deps.

    ::

      $ pip download \
          --only-binary=:all: \
          --platform any \
          --python-version 3 \
          --implementation py \
          --abi none \
          SomePackage

#. Even when overconstrained, this will still correctly fetch the pip universal wheel.

    ::

      $ pip download \
          --only-binary=:all: \
          --platform linux_x86_64 \
          --python-version 33 \
          --implementation cp \
          --abi cp34m \
          pip>=8
      $ ls pip-8.1.1-py2.py3-none-any.whl
      pip-8.1.1-py2.py3-none-any.whl
