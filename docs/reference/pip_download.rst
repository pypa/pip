
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
directory). This directory can later be passed as the value to
``pip install --find-links`` to facilitate offline or locked down package
installation.

``pip download`` with the ``--platform``, ``--interpreter-version``,
``--implementation``, ``--manylinux1``, and ``--abi`` options provides
the ability to fetch dependencies for an interpreter and system other
than the ones that pip is running on.  It is important to note that
these options all default to the current system/interpreter, and not
to the most restrictive constraints (e.g. platform any, abi none, etc).
To avoid fetching dependencies that happen to match the constraint
of the current interpreter (but not your target one), it is recommended
to specify all of these options if you are specifying one of them.
Generic dependencies (e.g. universal wheels, or dependencies with no
platform, abi, or implementation constraints) will still match
an over-constrained download requirement.


Options
*******

.. pip-command-options:: download

.. pip-index-options::


Examples
********

1. Download a package and all of its dependencies

  ::

    $ pip download SomePackage
    $ pip download -d . SomePackage  # equivalent to above
    $ pip download --no-index --find-links=/tmp/wheelhouse -d /tmp/otherwheelhouse SomePackage

2. Download a package and all of its dependencies with specific interpreter constraints

  ::

	$ pip download \
		# Force OSX 10.10 or lower compatibility. Since OSX deps
		# are forward compatible, this will also match
		# macosx-10_9_x86_64, macosx-10_8_x86_64, etc.
		# It will also match deps with platform any.
		--platform macosx-10_10_x86_64 \
		# Force Python 2.7 compatible deps.  This will still match more
		# generic interpreter versions, like '2'.
		--interpreter-version 27 \
		# Force CPython interpreter implementation.  This will still
		# match the most generic interpreter impelementation, 'py'.
		--implementation cp \
		SomePackage

	$ pip download \
		--platform linux_x86_64 --minilinux1 \ # Force linux or minilinux1
		--interpreter-version 3 \ # Allow any py3 minor rev
		--implementation cp \ # Force a specific interpreter implementation
		--abi cp34m \ # Force a specific abi (default is current one)
		SomePackage

	$ pip download \
		--platform any \ # Force platform agnostic deps
		--interpreter-version 3 \
		--implementation py \ # Force implementation agnostic deps
		--abi none \ # Force abi agnostic deps
		SomePackage

	$ pip download \ # Overconstrained; still fetches the pip universal wheel.
		--platform linux_x86_64 --minilinux1 \
		--interpreter-version 33 \
		--implementation cp \
		--abi cp34m \
		pip>=8
